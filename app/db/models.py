from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Float,
    Integer,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    config = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    runs = relationship("ReportRun", back_populates="report")
    versions = relationship("ReportVersion", back_populates="report")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    report_date = Column(Date, nullable=True)
    state = Column(String, nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    run_started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_finished_at = Column(DateTime, nullable=True)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    payload_hash = Column(String, nullable=True)

    report = relationship("Report", back_populates="runs")
    events = relationship("ReportRunEvent", back_populates="run")


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    payload_hash = Column(String, nullable=False)
    parsed_fields = Column(JSONB, nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("Report", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("report_id", "report_date", "payload_hash", name="uq_report_version_hash"),
    )


class ReportRunEvent(Base):
    __tablename__ = "report_run_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_run_id = Column(String, ForeignKey("report_runs.id"), nullable=False)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("ReportRun", back_populates="events")


class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report_links = relationship("RecipientReport", back_populates="recipient")


class RecipientReport(Base):
    __tablename__ = "recipient_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, ForeignKey("recipients.id"), nullable=False)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)

    recipient = relationship("Recipient", back_populates="report_links")

    __table_args__ = (
        UniqueConstraint("recipient_id", "report_id", name="uq_recipient_report"),
    )


class AlertState(Base):
    __tablename__ = "alert_state"

    report_id = Column(String, primary_key=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MarketOhlcv1d(Base):
    __tablename__ = "market_ohlcv_1d"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String, nullable=False)
    trade_date = Column(Date, nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    open_interest = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_market_ohlcv_symbol_date"),
        Index("ix_market_ohlcv_symbol_date", "symbol", "trade_date"),
    )


class MarketBatchJob(Base):
    __tablename__ = "market_batch_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False, unique=True)
    symbols = Column(JSONB, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    symbol = Column(String, primary_key=True)
    price = Column(Float, nullable=True)
    last_update = Column(String, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
