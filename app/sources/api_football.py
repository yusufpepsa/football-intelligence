"""API-Football istemcisi.

specs/000-veri-katmani.md Adım 3: rate limit ve retry burada. Başka
hiçbir yerde bu API'ye doğrudan HTTP çağrısı yapılmaz. Bu dosya şimdilik
sadece /fixtures uç noktasını uygular.
"""
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
RAW_DATA_DIR = Path("data/raw/api_football")

MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2
MIN_REQUEST_INTERVAL_SECONDS = 6  # ~10 istek/dakika — düşük plan için güvenli varsayılan
QUOTA_WARNING_THRESHOLD = 20  # günlük kalan istek bu sayının altına inerse uyar


class APIFootballError(Exception):
    pass


class APIFootballClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        if not self.api_key:
            raise APIFootballError("API_FOOTBALL_KEY tanımlı değil.")
        self.session = session or requests.Session()
        self._last_request_at: float = 0.0

    def get_fixtures(self, league_api_football_id: int, season: int, date_from: date, date_to: date) -> dict:
        """/fixtures uç noktası. Belirtilen lig ve tarih aralığındaki maçları döner."""
        params = {
            "league": league_api_football_id,
            "season": season,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "timezone": "UTC",
        }
        return self._get("/fixtures", params)

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining_wait = MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if remaining_wait > 0:
            time.sleep(remaining_wait)

    def _log_quota(self, headers) -> None:
        limit = headers.get("x-ratelimit-requests-limit")
        remaining = headers.get("x-ratelimit-requests-remaining")
        if limit is None or remaining is None:
            return
        logger.info("API Football kota: %s/%s istek kaldı", remaining, limit)
        try:
            if int(remaining) <= QUOTA_WARNING_THRESHOLD:
                logger.warning("API Football günlük kota sınırına yaklaşıldı: %s/%s kaldı", remaining, limit)
        except ValueError:
            pass

    def _get(self, path: str, params: dict) -> dict:
        url = f"{BASE_URL}{path}"
        headers = {"x-apisports-key": self.api_key}

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            self._wait_for_rate_limit()
            try:
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("İstek hatası (deneme %s/%s): %s", attempt, MAX_RETRIES, exc)
                time.sleep(INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)))
                continue
            finally:
                self._last_request_at = time.monotonic()

            self._log_quota(response.headers)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))))
                logger.warning("429 alındı, %s saniye bekleniyor (deneme %s/%s)", retry_after, attempt, MAX_RETRIES)
                time.sleep(retry_after)
                continue

            if response.status_code >= 500:
                logger.warning("Sunucu hatası %s (deneme %s/%s)", response.status_code, attempt, MAX_RETRIES)
                time.sleep(INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)))
                continue

            if response.status_code != 200:
                raise APIFootballError(f"API Football hatası: {response.status_code} {response.text[:500]}")

            payload = response.json()
            errors = payload.get("errors")
            if errors:
                raise APIFootballError(f"API Football yanıt hatası: {errors}")

            return payload

        raise APIFootballError(f"{MAX_RETRIES} denemeden sonra istek başarısız: {last_error}")


def save_raw_response(payload: dict, prefix: str) -> Path:
    """Ham yanıtı diske yazar. Parse hatası olsa bile ham veri kaybolmaz."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RAW_DATA_DIR / f"{prefix}_{timestamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False))
    return path
