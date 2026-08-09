"""football-data.co.uk istemcisi.

specs/000-veri-katmani.md Adım 4: anahtar gerekmez, CSV doğrudan indirilir.
docs/01-architecture.md'nin belirttiği "extra" ligler feed'i kullanılıyor:
https://www.football-data.co.uk/new/{fd_code}.csv - her ülke için TEK dosya,
birden fazla sezonu "Season" sütunuyla ayırt ediyor.

Gerçek başlık (doğrulandı): Country,League,Season,Date,Time,Home,Away,HG,AG,
Res,PSCH,PSCD,PSCA,MaxCH,MaxCD,MaxCA,AvgCH,AvgCD,AvgCA,BFECH,BFECD,BFECA,
B365CH,B365CD,B365CA

PSC* = Pinnacle kapanış oranı - docs/01-architecture.md gereği KULLANILMAZ.
MaxC*/AvgC* = piyasa maksimum/ortalama kapanış oranı - kullanılan bu ikisi.
Bu feed'de sadece KAPANIŞ oranı var, açılış oranı sütunu yok.
"""
import csv
import io
import logging
import time
from datetime import date, datetime

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.football-data.co.uk/new"
REQUEST_TIMEOUT = 30
MIN_REQUEST_INTERVAL_SECONDS = 2
MAX_RETRIES = 3


class FootballDataError(Exception):
    pass


_last_request_at = 0.0


def _wait_for_rate_limit() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    remaining = MIN_REQUEST_INTERVAL_SECONDS - elapsed
    if remaining > 0:
        time.sleep(remaining)


def fetch_league_rows(fd_code: str) -> list[dict]:
    """https://www.football-data.co.uk/new/{fd_code}.csv indirir, satırları dict olarak döner.

    fd_code doğrulanmamış olabilir (bkz. app/seed_data.py). 404 gelirse boş liste
    döner ve loglanır - çökmez, çünkü bu tek bir yanlış kodun bütün backfill'i
    durdurmaması gerekir.
    """
    url = f"{BASE_URL}/{fd_code}.csv"
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        _wait_for_rate_limit()
        global _last_request_at
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("football-data.co.uk istek hatası (deneme %s/%s, fd_code=%s): %s", attempt, MAX_RETRIES, fd_code, exc)
            time.sleep(2 * attempt)
            continue
        finally:
            _last_request_at = time.monotonic()

        if response.status_code == 404:
            logger.warning("football-data.co.uk 404 döndü (fd_code=%s, url=%s) - kod yanlış olabilir.", fd_code, url)
            return []

        if response.status_code >= 500:
            logger.warning("football-data.co.uk sunucu hatası %s (deneme %s/%s, fd_code=%s)", response.status_code, attempt, MAX_RETRIES, fd_code)
            time.sleep(2 * attempt)
            continue

        if response.status_code != 200:
            raise FootballDataError(f"football-data.co.uk hatası: {response.status_code} (fd_code={fd_code})")

        text = response.content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    raise FootballDataError(f"football-data.co.uk: {MAX_RETRIES} denemeden sonra başarısız (fd_code={fd_code}): {last_error}")


def season_start_year(season_value: str | None) -> int | None:
    """'2026' -> 2026, '2026/2027' -> 2026 (sezonun başladığı yıl). Ayrıştırılamazsa None."""
    if not season_value:
        return None
    part = season_value.split("/")[0].strip()
    try:
        return int(part)
    except ValueError:
        return None


def parse_match_date(date_str: str | None) -> date | None:
    """football-data.co.uk tarih formatı: DD/MM/YYYY."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def extract_closing_odds(row: dict) -> dict | None:
    """Piyasa ortalaması ve maksimum kapanış oranını döner. Pinnacle (PSC*) kullanılmaz.

    Döner: {"average": {"home":.., "draw":.., "away":..}, "max": {...}} veya
    ikisi de tamamen eksikse None.
    """
    average = {"home": _parse_float(row.get("AvgCH")), "draw": _parse_float(row.get("AvgCD")), "away": _parse_float(row.get("AvgCA"))}
    maximum = {"home": _parse_float(row.get("MaxCH")), "draw": _parse_float(row.get("MaxCD")), "away": _parse_float(row.get("MaxCA"))}

    average_complete = all(v is not None for v in average.values())
    maximum_complete = all(v is not None for v in maximum.values())

    if not average_complete and not maximum_complete:
        return None

    return {
        "average": average if average_complete else None,
        "max": maximum if maximum_complete else None,
    }
