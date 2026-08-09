"""Komut satırı arayüzü. `python -m app.cli <komut>` ile çalıştırılır."""
import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher

from sqlalchemy import text

from app.db import bulk_insert, get_engine
from app.seed_data import CROSS_YEAR_SEASON_LEAGUES, LEAGUES
from app.sources import football_data
from app.sources.api_football import APIFootballClient, APIFootballError, save_raw_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FETCH_DAYS_AHEAD = 7
BACKFILL_SEASONS = [2023, 2024, 2025, 2026]
FUZZY_MATCH_THRESHOLD = 0.9

# API-Football fixture.status.short -> fixtures.status
STATUS_MAP = {
    "NS": "scheduled",
    "TBD": "scheduled",
    "PST": "postponed",
    "CANC": "cancelled",
    "ABD": "cancelled",
    "AWD": "finished",
    "WO": "finished",
    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
}


def _map_status(short_code: str) -> str:
    return STATUS_MAP.get(short_code, "scheduled")


def _season_for(today: date, api_football_league_id: int) -> int:
    if api_football_league_id in CROSS_YEAR_SEASON_LEAGUES and today.month < 7:
        return today.year - 1
    return today.year


def cmd_seed() -> None:
    engine = get_engine()
    inserted = 0
    with engine.begin() as conn:
        for league in LEAGUES:
            result = conn.execute(
                text(
                    """
                    INSERT INTO leagues (name, country, api_football_id, fd_code)
                    VALUES (:name, :country, :api_football_id, :fd_code)
                    ON CONFLICT (api_football_id) DO NOTHING
                    """
                ),
                {
                    "name": league["name"],
                    "country": league["country"],
                    "api_football_id": league["api_football_id"],
                    "fd_code": league["fd_code"],
                },
            )
            inserted += result.rowcount
    already_present = len(LEAGUES) - inserted
    logger.info(
        "%s lig eklendi, %s zaten vardı (toplam %s lig tanımlı).",
        inserted, already_present, len(LEAGUES),
    )


def _extract_team_refs(items: list[dict]) -> dict[int, str]:
    """items içindeki bütün ev/deplasman takımlarını (api_football_id -> isim) çıkarır."""
    result: dict[int, str] = {}
    for item in items:
        try:
            teams = item["teams"]
            result[teams["home"]["id"]] = teams["home"]["name"]
            result[teams["away"]["id"]] = teams["away"]["name"]
        except (KeyError, TypeError):
            continue
    return result


def _bulk_resolve_teams(conn, league_id: int, team_names: dict[int, str]) -> dict[int, int]:
    """api_football_id -> teams.id eşlemesi. Tek toplu upsert + tek toplu SELECT."""
    if not team_names:
        return {}

    rows = [{"league_id": league_id, "name": name, "api_football_id": api_id} for api_id, name in team_names.items()]
    bulk_insert(
        conn, "teams", ["league_id", "name", "api_football_id"], rows,
        conflict_clause="ON CONFLICT (api_football_id) DO NOTHING",
    )

    result = conn.execute(
        text("SELECT id, api_football_id FROM teams WHERE api_football_id = ANY(:ids)"),
        {"ids": list(team_names.keys())},
    ).all()
    return {r.api_football_id: r.id for r in result}


def _build_fixture_rows(league_id: int, items: list[dict], team_id_map: dict[int, int]) -> tuple[list[dict], int]:
    """Döner: (fixtures'a yazılacak satırlar, bozuk veri nedeniyle atlanan sayısı)."""
    rows = []
    skipped = 0
    for item in items:
        try:
            fixture = item["fixture"]
            teams = item["teams"]
            goals = item.get("goals") or {}
            score = item.get("score") or {}
            halftime = score.get("halftime") or {}
            rows.append({
                "league_id": league_id,
                "home_team_id": team_id_map[teams["home"]["id"]],
                "away_team_id": team_id_map[teams["away"]["id"]],
                "kickoff_utc": fixture["date"],
                "season": str(item["league"]["season"]),
                "status": _map_status(fixture["status"]["short"]),
                "api_football_id": fixture["id"],
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "home_goals_ht": halftime.get("home"),
                "away_goals_ht": halftime.get("away"),
            })
        except (KeyError, TypeError) as exc:
            fixture_id = (item.get("fixture") or {}).get("id", "?")
            logger.warning("Fikstür atlandı (id=%s): %s", fixture_id, exc)
            skipped += 1
    return rows, skipped


def _ingest_fixtures_payload(engine, league, payload: dict) -> int:
    """Ham yanıtı arşivler, takımları ve fikstürleri TEK transaction'da toplu yazar.

    Önceki sürüm her fikstürü ayrı bir INSERT (+ takım için ayrı SELECT/INSERT)
    olarak yazıyordu - uzak bir Postgres'e karşı bu, maç başına bir round-trip
    demekti (306 maç ~3 dakika). Artık bütün takımlar tek INSERT, bütün fikstürler
    tek INSERT ile yazılıyor.
    """
    try:
        save_raw_response(payload, prefix=f"fixtures_league{league['api_football_id']}")
    except OSError as exc:
        logger.warning("Ham yanıt diske yazılamadı (%s): %s", league["name"], exc)

    items = payload.get("response", [])
    if not items:
        return 0

    team_names = _extract_team_refs(items)

    with engine.begin() as conn:
        team_id_map = _bulk_resolve_teams(conn, league["id"], team_names)
        fixture_rows, skipped = _build_fixture_rows(league["id"], items, team_id_map)
        bulk_insert(
            conn, "fixtures",
            ["league_id", "home_team_id", "away_team_id", "kickoff_utc", "season", "status",
             "api_football_id", "home_goals", "away_goals", "home_goals_ht", "away_goals_ht"],
            fixture_rows,
            conflict_clause="ON CONFLICT (api_football_id) DO NOTHING",
        )

    if skipped:
        logger.warning("%s: %s fikstür bozuk veri nedeniyle atlandı.", league["name"], skipped)

    return len(items)


def _process_league(engine, client: APIFootballClient, league, today: date, date_to: date) -> int:
    season = _season_for(today, league["api_football_id"])
    logger.info(
        "Fikstür çekiliyor: %s (api_football_id=%s, season=%s)",
        league["name"], league["api_football_id"], season,
    )

    payload = client.get_fixtures(
        league_api_football_id=league["api_football_id"],
        season=season,
        date_from=today,
        date_to=date_to,
    )

    n = _ingest_fixtures_payload(engine, league, payload)
    logger.info("%s: %s maç döndü.", league["name"], n)
    return n


def _process_league_season(engine, client: APIFootballClient, league, season: int) -> int:
    """Belirtilen sezonun tamamını çeker (tarih aralığı yok - API-Football league+season için
    sezonun tüm fikstürlerini döner)."""
    payload = client.get_fixtures(league_api_football_id=league["api_football_id"], season=season)
    return _ingest_fixtures_payload(engine, league, payload)


def cmd_fetch() -> None:
    engine = get_engine()
    client = APIFootballClient()

    with engine.begin() as conn:
        active_leagues = conn.execute(
            text("SELECT id, api_football_id, name FROM leagues WHERE is_active = true ORDER BY id")
        ).mappings().all()

    logger.info(
        "%s aktif lig bulundu: %s",
        len(active_leagues),
        ", ".join(f"{l['name']} (id={l['id']})" for l in active_leagues) or "-",
    )

    if not active_leagues:
        logger.warning("Aktif lig bulunamadı. Önce 'make seed' çalıştırılmalı.")
        return

    today = date.today()
    date_to = today + timedelta(days=FETCH_DAYS_AHEAD)

    total_fixtures = 0
    for league in active_leagues:
        try:
            total_fixtures += _process_league(engine, client, league, today, date_to)
        except Exception as exc:
            # Bir ligin başarısız olması diğerlerinin işlenmesini engellemez.
            logger.error("Lig işlenemedi (%s): %s", league["name"], exc)
            continue

    logger.info("Toplam %s maç işlendi.", total_fixtures)


def cmd_backfill_seasons() -> None:
    """specs/000-veri-katmani.md: geçmiş sezonların tamamını (tarih penceresi olmadan) çeker.

    Sezon numaraları (2023-2026) her lig için AYNI şekilde kullanılır. API-Football'da
    "season" parametresi her zaman sezonun başladığı yılı ifade eder; yaz-kış arası
    oynanan liglerde (bkz. CROSS_YEAR_SEASON_LEAGUES) de bu numaralandırma aynıdır -
    örn. season=2023, İsviçre için Temmuz 2023 - Haziran 2024 sezonunu getirir.
    """
    engine = get_engine()
    client = APIFootballClient()

    with engine.begin() as conn:
        active_leagues = conn.execute(
            text("SELECT id, api_football_id, name FROM leagues WHERE is_active = true ORDER BY id")
        ).mappings().all()

    logger.info(
        "%s aktif lig bulundu: %s",
        len(active_leagues),
        ", ".join(f"{l['name']} (id={l['id']})" for l in active_leagues) or "-",
    )

    if not active_leagues:
        logger.warning("Aktif lig bulunamadı. Önce 'make seed' çalıştırılmalı.")
        return

    total_fixtures = 0
    for league in active_leagues:
        for season in BACKFILL_SEASONS:
            try:
                n = _process_league_season(engine, client, league, season)
            except Exception as exc:
                logger.error("Lig/sezon işlenemedi (%s, sezon=%s): %s", league["name"], season, exc)
                continue
            logger.info("%s sezon %s: %s maç geldi.", league["name"], season, n)
            total_fixtures += n

    logger.info("Toplam %s maç işlendi (backfill-seasons).", total_fixtures)


def _resolve_team_name(
    raw_name: str,
    alias_map: dict[str, int],
    team_by_name: dict[str, int],
    team_names: list[str],
    new_aliases: list[dict],
) -> int | None:
    """team_aliases -> tam isim -> bulanık eşleştirme (eşik FUZZY_MATCH_THRESHOLD) sırasıyla dener."""
    if raw_name in alias_map:
        return alias_map[raw_name]

    if raw_name in team_by_name:
        team_id = team_by_name[raw_name]
        alias_map[raw_name] = team_id
        new_aliases.append({"team_id": team_id, "source": "football_data", "alias": raw_name})
        return team_id

    best_name, best_ratio = None, 0.0
    for name in team_names:
        ratio = SequenceMatcher(None, raw_name.lower(), name.lower()).ratio()
        if ratio > best_ratio:
            best_name, best_ratio = name, ratio

    if best_name is not None and best_ratio >= FUZZY_MATCH_THRESHOLD:
        team_id = team_by_name[best_name]
        alias_map[raw_name] = team_id
        new_aliases.append({"team_id": team_id, "source": "football_data", "alias": raw_name})
        return team_id

    return None


def _backfill_league_odds(engine, league) -> tuple[int, int]:
    """Döner: (eşleşen maç sayısı, eşleşmeyen kayıt sayısı)."""
    rows = football_data.fetch_league_rows(league["fd_code"])
    rows = [r for r in rows if football_data.season_start_year(r.get("Season")) in BACKFILL_SEASONS]
    logger.info("%s: CSV'de hedef sezonlarda %s satır bulundu.", league["name"], len(rows))

    if not rows:
        return 0, 0

    with engine.begin() as conn:
        teams = conn.execute(
            text("SELECT id, name FROM teams WHERE league_id = :league_id"),
            {"league_id": league["id"]},
        ).all()
        existing_aliases = conn.execute(
            text(
                """
                SELECT alias, team_id FROM team_aliases
                WHERE source = 'football_data'
                  AND team_id IN (SELECT id FROM teams WHERE league_id = :league_id)
                """
            ),
            {"league_id": league["id"]},
        ).all()
        fixtures = conn.execute(
            text("SELECT id, home_team_id, away_team_id, kickoff_utc FROM fixtures WHERE league_id = :league_id"),
            {"league_id": league["id"]},
        ).all()

    team_by_name = {t.name: t.id for t in teams}
    team_names = list(team_by_name.keys())
    alias_map = {a.alias: a.team_id for a in existing_aliases}
    fixture_lookup = {
        (f.home_team_id, f.away_team_id, f.kickoff_utc.date()): (f.id, f.kickoff_utc) for f in fixtures
    }

    new_aliases: list[dict] = []
    unmatched_rows: list[dict] = []
    odds_rows: list[dict] = []
    matched = 0
    unmatched = 0

    for row in rows:
        home_raw = (row.get("Home") or "").strip()
        away_raw = (row.get("Away") or "").strip()
        match_date = football_data.parse_match_date(row.get("Date"))

        home_id = _resolve_team_name(home_raw, alias_map, team_by_name, team_names, new_aliases) if home_raw else None
        away_id = _resolve_team_name(away_raw, alias_map, team_by_name, team_names, new_aliases) if away_raw else None

        if home_id is None or away_id is None or match_date is None:
            unmatched += 1
            unmatched_rows.append({
                "source": "football_data",
                "raw_home": home_raw or None,
                "raw_away": away_raw or None,
                "raw_date": match_date,
                "seen_at": datetime.now(timezone.utc),
            })
            continue

        # Bazı geç saat maçlarında yerel tarih ile UTC tarihi bir gün kayabilir.
        fixture_entry = (
            fixture_lookup.get((home_id, away_id, match_date))
            or fixture_lookup.get((home_id, away_id, match_date - timedelta(days=1)))
            or fixture_lookup.get((home_id, away_id, match_date + timedelta(days=1)))
        )
        if fixture_entry is None:
            unmatched += 1
            unmatched_rows.append({
                "source": "football_data",
                "raw_home": home_raw,
                "raw_away": away_raw,
                "raw_date": match_date,
                "seen_at": datetime.now(timezone.utc),
            })
            continue

        fixture_id, kickoff_utc = fixture_entry
        matched += 1

        odds = football_data.extract_closing_odds(row)
        if odds is None:
            continue  # takım+tarih eşleşti ama bu maç için oran verisi yok

        if odds["average"] is not None:
            odds_rows.append({
                "fixture_id": fixture_id, "source": "football_data_avg", "market": "1x2",
                "odds": odds["average"], "captured_at": kickoff_utc, "is_closing": True,
            })
        if odds["max"] is not None:
            odds_rows.append({
                "fixture_id": fixture_id, "source": "football_data_max", "market": "1x2",
                "odds": odds["max"], "captured_at": kickoff_utc, "is_closing": True,
            })

    with engine.begin() as conn:
        bulk_insert(
            conn, "team_aliases", ["team_id", "source", "alias"], new_aliases,
            conflict_clause="ON CONFLICT (source, alias) DO NOTHING",
        )
        bulk_insert(
            conn, "odds_snapshots",
            ["fixture_id", "source", "market", "odds", "captured_at", "is_closing"],
            odds_rows,
            conflict_clause="ON CONFLICT (fixture_id, source, market, captured_at) DO NOTHING",
            casts={"odds": "::jsonb"},
        )
        bulk_insert(
            conn, "unmatched_fixtures",
            ["source", "raw_home", "raw_away", "raw_date", "seen_at"],
            unmatched_rows,
        )

    return matched, unmatched


def cmd_backfill_odds() -> None:
    """specs/000-veri-katmani.md Adım 4-5: football-data.co.uk'ten kapanış oranı çeker.

    Anahtar gerekmez. leagues.fd_code doğrulanmamış olabilir - 404 gelirse
    app/sources/football_data.py loglar, bu lig atlanır, diğerleri etkilenmez.
    """
    engine = get_engine()

    with engine.begin() as conn:
        active_leagues = conn.execute(
            text("SELECT id, name, fd_code FROM leagues WHERE is_active = true ORDER BY id")
        ).mappings().all()

    logger.info("%s aktif lig bulundu.", len(active_leagues))

    if not active_leagues:
        logger.warning("Aktif lig bulunamadı. Önce 'make seed' çalıştırılmalı.")
        return

    total_matched = 0
    total_unmatched = 0
    for league in active_leagues:
        if not league["fd_code"]:
            logger.warning("%s için fd_code tanımlı değil, atlanıyor.", league["name"])
            continue
        try:
            matched, unmatched = _backfill_league_odds(engine, league)
        except Exception as exc:
            logger.error("Oran backfill başarısız (%s): %s", league["name"], exc)
            continue
        logger.info("%s: %s maç eşleşti, %s eşleşmedi.", league["name"], matched, unmatched)
        total_matched += matched
        total_unmatched += unmatched

    logger.info("Toplam: %s eşleşti, %s eşleşmedi.", total_matched, total_unmatched)


def cmd_report() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        leagues = conn.execute(
            text("SELECT id, name, country, api_football_id, is_active FROM leagues ORDER BY id")
        ).mappings().all()

    print(f"{len(leagues)} lig bulundu.\n", flush=True)

    for league in leagues:
        try:
            with engine.begin() as conn:
                stats = conn.execute(
                    text(
                        """
                        SELECT count(*) AS n, min(kickoff_utc) AS earliest, max(kickoff_utc) AS latest
                        FROM fixtures WHERE league_id = :league_id
                        """
                    ),
                    {"league_id": league["id"]},
                ).mappings().one()

                sample_teams = conn.execute(
                    text("SELECT name FROM teams WHERE league_id = :league_id ORDER BY id LIMIT 3"),
                    {"league_id": league["id"]},
                ).scalars().all()

                odds_coverage = conn.execute(
                    text(
                        """
                        SELECT count(DISTINCT os.fixture_id) AS n
                        FROM odds_snapshots os
                        JOIN fixtures f ON f.id = os.fixture_id
                        WHERE f.league_id = :league_id AND os.is_closing = true
                        """
                    ),
                    {"league_id": league["id"]},
                ).scalar_one()

            status = "" if league["is_active"] else " [PASİF]"
            print(f"{league['name']} ({league['country']}, api_football_id={league['api_football_id']}, league_id={league['id']}){status}", flush=True)
            print(f"  maç sayısı: {stats['n']}", flush=True)
            if stats["n"]:
                print(f"  en erken: {stats['earliest']}  en geç: {stats['latest']}", flush=True)
            print(f"  örnek takımlar: {', '.join(sample_teams) if sample_teams else '(yok)'}", flush=True)
            print(f"  kapanış oranı olan maç: {odds_coverage}", flush=True)
            print(flush=True)
        except Exception as exc:
            # Bir lig için özet alınamaması diğerlerinin basılmasını engellemesin.
            print(f"  HATA: {league['name']} için özet alınamadı: {exc}\n", flush=True)

    with engine.begin() as conn:
        unmatched_stats = conn.execute(
            text(
                "SELECT count(*) AS total, count(*) FILTER (WHERE NOT resolved) AS unresolved FROM unmatched_fixtures"
            )
        ).mappings().one()
    print(
        f"Eşleşmeyen kayıt (unmatched_fixtures): {unmatched_stats['total']} (çözülmemiş: {unmatched_stats['unresolved']})",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Lig listesini veritabanına yükle")
    subparsers.add_parser("fetch", help="Önümüzdeki günlerin maçlarını çek")
    subparsers.add_parser("backfill-seasons", help="Son 4 sezonun (2023-2026) fikstürlerini çek")
    subparsers.add_parser("backfill-odds", help="football-data.co.uk'ten kapanış oranlarını çek")
    subparsers.add_parser("report", help="Lig başına maç/takım/oran özetini yazdır")

    args = parser.parse_args(argv)

    try:
        if args.command == "seed":
            cmd_seed()
        elif args.command == "fetch":
            cmd_fetch()
        elif args.command == "backfill-seasons":
            cmd_backfill_seasons()
        elif args.command == "backfill-odds":
            cmd_backfill_odds()
        elif args.command == "report":
            cmd_report()
    except APIFootballError as exc:
        logger.error("API Football hatası: %s", exc)
        return 1
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
