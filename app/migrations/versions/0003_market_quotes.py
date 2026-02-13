"""market quotes table

Revision ID: 0003_market_quotes
Revises: 0002_market_data
Create Date: 2026-02-12 00:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_market_quotes"
down_revision = "0002_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_quotes",
        sa.Column("symbol", sa.String(), primary_key=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("last_update", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("market_quotes")
