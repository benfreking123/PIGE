"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-06 00:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "report_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("report_id", sa.String(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("run_started_at", sa.DateTime(), nullable=False),
        sa.Column("run_finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(), nullable=True),
    )
    op.create_table(
        "report_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("report_id", sa.String(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("parsed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("report_id", "report_date", "payload_hash", name="uq_report_version_hash"),
    )
    op.create_table(
        "report_run_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("report_run_id", sa.String(), sa.ForeignKey("report_runs.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "recipients",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "recipient_reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("recipient_id", sa.String(), sa.ForeignKey("recipients.id"), nullable=False),
        sa.Column("report_id", sa.String(), sa.ForeignKey("reports.id"), nullable=False),
        sa.UniqueConstraint("recipient_id", "report_id", name="uq_recipient_report"),
    )
    op.create_table(
        "alert_state",
        sa.Column("report_id", sa.String(), primary_key=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alert_state")
    op.drop_table("recipient_reports")
    op.drop_table("recipients")
    op.drop_table("report_run_events")
    op.drop_table("report_versions")
    op.drop_table("report_runs")
    op.drop_table("reports")
