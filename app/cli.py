"""Komut satırı arayüzü. `python -m app.cli <komut>` ile çalıştırılır."""
import argparse
import logging
import sys
from datetime import date, timedelta

from sqlalchemy import text

from app.db import get_engine
from app.seed_data import CROSS_YEAR_SEASON_LEAGUES, LEAGUES
from app.sources.api_football import APIFootballClient, APIFootballError, save_raw_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FETCH_DAYS_AHEAD = 7

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
    with engine.begin() as conn:
        for league in LEAGUES:
            conn.execute(
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
    logger.info("%s lig eklendi/kontrol edildi.", len(LEAGUES))


def _get_or_create_team(conn, league_id: int, api_football_id: int, name: str) -> int:
    row = conn.execute(
        text("SELECT id FROM teams WHERE api_football_id = :api_football_id"),
        {"api_football_id": api_football_id},
    ).first()
    if row:
        return row.id

    row = conn.execute(
        text(
            """
            INSERT INTO teams (league_id, name, api_football_id)
            VALUES (:league_id, :name, :api_football_id)
            RETURNING id
            """
        ),
        {"league_id": league_id, "name": name, "api_football_id": api_football_id},
    ).first()
    return row.id


def _upsert_fixture(conn, league_id: int, item: dict) -> None:
    fixture = item["fixture"]
    teams = item["teams"]
    goals = item.get("goals") or {}
    score = item.get("score") or {}
    halftime = score.get("halftime") or {}

    home_team_id = _get_or_create_team(conn, league_id, teams["home"]["id"], teams["home"]["name"])
    away_team_id = _get_or_create_team(conn, league_id, teams["away"]["id"], teams["away"]["name"])

    conn.execute(
        text(
            """
            INSERT INTO fixtures (
                league_id, home_team_id, away_team_id, kickoff_utc, season, status,
                api_football_id, home_goals, away_goals, home_goals_ht, away_goals_ht
            ) VALUES (
                :league_id, :home_team_id, :away_team_id, :kickoff_utc, :season, :status,
                :api_football_id, :home_goals, :away_goals, :home_goals_ht, :away_goals_ht
            )
            ON CONFLICT (api_football_id) DO NOTHING
            """
        ),
        {
            "league_id": league_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "kickoff_utc": fixture["date"],
            "season": str(item["league"]["season"]),
            "status": _map_status(fixture["status"]["short"]),
            "api_football_id": fixture["id"],
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "home_goals_ht": halftime.get("home"),
            "away_goals_ht": halftime.get("away"),
        },
    )


def cmd_fetch() -> None:
    engine = get_engine()
    client = APIFootballClient()

    with engine.begin() as conn:
        active_leagues = conn.execute(
            text("SELECT id, api_football_id, name FROM leagues WHERE is_active = true")
        ).mappings().all()

    if not active_leagues:
        logger.warning("Aktif lig bulunamadı. Önce 'make seed' çalıştırılmalı.")
        return

    today = date.today()
    date_to = today + timedelta(days=FETCH_DAYS_AHEAD)

    total_fixtures = 0
    for league in active_leagues:
        season = _season_for(today, league["api_football_id"])
        logger.info(
            "Fikstür çekiliyor: %s (api_football_id=%s, season=%s)",
            league["name"], league["api_football_id"], season,
        )
        try:
            payload = client.get_fixtures(
                league_api_football_id=league["api_football_id"],
                season=season,
                date_from=today,
                date_to=date_to,
            )
        except APIFootballError as exc:
            logger.error("Fikstür çekilemedi (%s): %s", league["name"], exc)
            continue

        save_raw_response(payload, prefix=f"fixtures_league{league['api_football_id']}")

        fixtures = payload.get("response", [])
        logger.info("%s: %s maç döndü.", league["name"], len(fixtures))

        with engine.begin() as conn:
            for item in fixtures:
                try:
                    _upsert_fixture(conn, league_id=league["id"], item=item)
                except (KeyError, TypeError) as exc:
                    fixture_id = (item.get("fixture") or {}).get("id", "?")
                    logger.warning("Fikstür işlenemedi (id=%s): %s", fixture_id, exc)

        total_fixtures += len(fixtures)

    logger.info("Toplam %s maç işlendi.", total_fixtures)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Lig listesini veritabanına yükle")
    subparsers.add_parser("fetch", help="Önümüzdeki günlerin maçlarını çek")

    args = parser.parse_args(argv)

    try:
        if args.command == "seed":
            cmd_seed()
        elif args.command == "fetch":
            cmd_fetch()
    except APIFootballError as exc:
        logger.error("API Football hatası: %s", exc)
        return 1
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
