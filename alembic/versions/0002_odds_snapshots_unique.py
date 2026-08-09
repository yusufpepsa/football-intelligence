"""odds_snapshots'a unique kısıt - toplu/idempotent oran yazımı için

Revision ID: 0002_odds_snapshots_unique
Revises: 0001_initial_schema
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_odds_snapshots_unique"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # captured_at kısıtın parçası: aynı fixture/source/market için farklı zamanlarda
    # alınmış birden fazla anlık görüntüye izin verir (örn. ileride canlı oran takibi),
    # ama aynı backfill çalıştırmasının aynı satırı iki kez yazmasını engeller.
    op.create_unique_constraint(
        "uq_odds_snapshots_fixture_source_market_captured_at",
        "odds_snapshots",
        ["fixture_id", "source", "market", "captured_at"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_odds_snapshots_fixture_source_market_captured_at",
        "odds_snapshots",
        type_="unique",
    )
