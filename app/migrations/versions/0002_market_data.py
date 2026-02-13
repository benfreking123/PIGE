"""market data tables

Revision ID: 0002_market_data
Revises: 0001_initial
Create Date: 2026-02-12 00:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_market_data"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_ohlcv_1d",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("open_interest", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_market_ohlcv_symbol_date"),
    )
    op.create_index(
        "ix_market_ohlcv_symbol_date",
        "market_ohlcv_1d",
        ["symbol", "trade_date"],
    )
    op.create_table(
        "market_batch_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("symbols", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_market_batch_job_id"),
    )


def downgrade() -> None:
    op.drop_table("market_batch_jobs")
    op.drop_index("ix_market_ohlcv_symbol_date", table_name="market_ohlcv_1d")
    op.drop_table("market_ohlcv_1d")
