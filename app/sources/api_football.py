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

    def get_fixtures(
        self,
        league_api_football_id: int,
        season: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """/fixtures uç noktası.

        date_from/date_to verilirse o aralıkla sınırlar (günlük fetch).
        Verilmezse API-Football league+season için sezonun tamamını döner
        (geçmiş sezon backfill'i için).
        """
        params = {"league": league_api_football_id, "season": season, "timezone": "UTC"}
        if date_from is not None:
            params["from"] = date_from.isoformat()
        if date_to is not None:
            params["to"] = date_to.isoformat()
        return self._get("/fixtures", params)

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining_wait = MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if remaining_wait > 0:
            time.sleep(remaining_wait)

    def _log_quota(self, headers, status_code: int) -> None:
        """Günlük ve dakikalık kotayı ayrı ayrı loglar.

        API-Football iki farklı başlık çifti döner: "requests" geçen isimler
        günlük kotayı, geçmeyenler dakikalık kotayı gösterir. İkisi
        karıştırılırsa (örn. dakikalık sayaç günlük sanılırsa) kota normalde
        düşerken aniden yükseliyormuş gibi görünür — bu yüzden ikisi burada
        açıkça ayrı etiketlerle loglanır.
        """
        tag = "" if status_code == 200 else f" [HTTP {status_code} yanıtı, güvenilir olmayabilir]"

        daily_limit = headers.get("x-ratelimit-requests-limit")
        daily_remaining = headers.get("x-ratelimit-requests-remaining")
        if daily_limit is not None and daily_remaining is not None:
            logger.info("API Football günlük kota: %s/%s kaldı%s", daily_remaining, daily_limit, tag)
            try:
                if int(daily_remaining) <= QUOTA_WARNING_THRESHOLD:
                    logger.warning(
                        "API Football günlük kota sınırına yaklaşıldı: %s/%s kaldı", daily_remaining, daily_limit
                    )
            except ValueError:
                pass

        minute_limit = headers.get("X-RateLimit-Limit")
        minute_remaining = headers.get("X-RateLimit-Remaining")
        if minute_limit is not None and minute_remaining is not None:
            logger.info("API Football dakikalık kota: %s/%s kaldı%s", minute_remaining, minute_limit, tag)

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

            self._log_quota(response.headers, response.status_code)

            if response.status_code == 429:
                backoff = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                retry_after_header = response.headers.get("Retry-After")
                if retry_after_header is not None:
                    try:
                        backoff = int(retry_after_header)
                    except ValueError:
                        # Retry-After bir HTTP-tarihi de olabilir (RFC 7231);
                        # ayrıştıramazsak hesaplanan backoff'a düş, çökme.
                        logger.warning("Retry-After ayrıştırılamadı: %r, hesaplanan bekleme kullanılıyor", retry_after_header)
                logger.warning("429 alındı, %s saniye bekleniyor (deneme %s/%s)", backoff, attempt, MAX_RETRIES)
                time.sleep(backoff)
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
