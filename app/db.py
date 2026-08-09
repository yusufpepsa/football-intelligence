import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

load_dotenv()


def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL tanımlı değil (.env veya ortam değişkeni).")
    return create_engine(database_url)


def bulk_insert(
    conn: Connection,
    table: str,
    columns: list[str],
    rows: list[dict],
    conflict_clause: str = "",
    casts: dict[str, str] | None = None,
) -> None:
    """Birden çok satırı TEK INSERT ile yazar (satır başına ayrı round-trip yerine).

    Uzak, ağ üzerinden erişilen bir Postgres'e (Neon/Supabase) karşı satır başına
    INSERT çok yavaştır - her satır ayrı bir round-trip'tir. Bu yüzden bütün toplu
    veri yazımı (fetch, backfill-seasons, backfill-odds) buradan geçer.

    casts: örn. {"odds": "::jsonb"} - jsonb sütunları için değer json.dumps ile
    metne çevrilir ve SQL'de açıkça cast edilir.
    """
    if not rows:
        return

    casts = casts or {}
    values_clauses = []
    params: dict = {}
    for i, row in enumerate(rows):
        placeholders = []
        for col in columns:
            key = f"{col}_{i}"
            cast = casts.get(col, "")
            # SQLAlchemy'nin text() bağlama parametresi ayracı ":ad" hemen ardından
            # "::" (Postgres cast operatörü) gelirse parametreyi tanımıyor, olduğu gibi
            # metne geçiriyor - araya boşluk koymak bunu çözüyor.
            placeholders.append(f":{key} {cast}" if cast else f":{key}")
            value = row[col]
            if cast == "::jsonb" and not isinstance(value, str):
                value = json.dumps(value)
            params[key] = value
        values_clauses.append(f"({', '.join(placeholders)})")

    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES {', '.join(values_clauses)} {conflict_clause}"
    conn.execute(text(sql), params)
