"""ilk şema - docs/02-data-model.md

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("api_football_id", sa.Integer(), unique=True),
        sa.Column("fd_code", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("api_football_id", sa.Integer(), unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "team_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("source", sa.Text()),
        sa.Column("alias", sa.Text()),
        sa.UniqueConstraint("source", "alias"),
    )

    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("kickoff_utc", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("season", sa.Text()),
        sa.Column("status", sa.Text()),
        sa.Column("api_football_id", sa.Integer(), unique=True),
        sa.Column("home_goals", sa.Integer(), nullable=True),
        sa.Column("away_goals", sa.Integer(), nullable=True),
        sa.Column("home_goals_ht", sa.Integer(), nullable=True),
        sa.Column("away_goals_ht", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_fixtures_kickoff_utc", "fixtures", ["kickoff_utc"])
    op.create_index("ix_fixtures_league_id_kickoff_utc", "fixtures", ["league_id", "kickoff_utc"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("predictor_name", sa.Text(), nullable=False),
        sa.Column("predictor_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("probabilities", JSONB(), nullable=False),
        sa.Column("predicted_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("input_snapshot", JSONB(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # sonradan doldurulan alanlar
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("settled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closing_odds", JSONB(), nullable=True),
        sa.Column("closing_source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("fixture_id", "predictor_name", "predictor_version", "market"),
    )
    op.create_index("ix_predictions_predicted_at", "predictions", ["predicted_at"])
    op.create_index("ix_predictions_predictor_name_market", "predictions", ["predictor_name", "market"])

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("source", sa.Text()),
        sa.Column("market", sa.Text()),
        sa.Column("odds", JSONB()),
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_closing", sa.Boolean()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_odds_snapshots_fixture_source_market", "odds_snapshots", ["fixture_id", "source", "market"])

    op.create_table(
        "bets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("stake", sa.Numeric(10, 2)),
        sa.Column("odds_taken", sa.Numeric(6, 3)),
        sa.Column("is_paper", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("placed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("pnl", sa.Numeric(10, 2), nullable=True),
    )

    op.create_table(
        "metrics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("predictor_name", sa.Text()),
        sa.Column("market", sa.Text()),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=True),
        sa.Column("n", sa.Integer()),
        sa.Column("brier", sa.Numeric()),
        sa.Column("log_loss", sa.Numeric()),
        sa.Column("calibration", JSONB()),
        sa.Column("roi_vs_closing", sa.Numeric(), nullable=True),
    )

    op.create_table(
        "unmatched_fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.Text()),
        sa.Column("raw_home", sa.Text()),
        sa.Column("raw_away", sa.Text()),
        sa.Column("raw_date", sa.Date()),
        sa.Column("seen_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Değişmez kural: predicted_at, ilişkili maçın kickoff_utc'sinden önce olmalı.
    # predictions güncellenmediği için sadece INSERT'te kontrol yeterlidir.
    op.execute(
        """
        CREATE FUNCTION check_predicted_before_kickoff() RETURNS TRIGGER AS $$
        DECLARE
            v_kickoff TIMESTAMPTZ;
        BEGIN
            SELECT kickoff_utc INTO v_kickoff FROM fixtures WHERE id = NEW.fixture_id;
            IF v_kickoff IS NULL THEN
                RAISE EXCEPTION 'fixture_id % bulunamadı', NEW.fixture_id;
            END IF;
            IF NEW.predicted_at >= v_kickoff THEN
                RAISE EXCEPTION 'predicted_at (%) kickoff_utc (%) sonrasında olamaz', NEW.predicted_at, v_kickoff;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_predictions_predicted_before_kickoff
        BEFORE INSERT ON predictions
        FOR EACH ROW EXECUTE FUNCTION check_predicted_before_kickoff();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_predictions_predicted_before_kickoff ON predictions;")
    op.execute("DROP FUNCTION IF EXISTS check_predicted_before_kickoff();")

    op.drop_table("unmatched_fixtures")
    op.drop_table("metrics_snapshots")
    op.drop_table("bets")
    op.drop_index("ix_odds_snapshots_fixture_source_market", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_index("ix_predictions_predictor_name_market", table_name="predictions")
    op.drop_index("ix_predictions_predicted_at", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_fixtures_league_id_kickoff_utc", table_name="fixtures")
    op.drop_index("ix_fixtures_kickoff_utc", table_name="fixtures")
    op.drop_table("fixtures")
    op.drop_table("team_aliases")
    op.drop_table("teams")
    op.drop_table("leagues")
