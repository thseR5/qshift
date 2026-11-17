"""Tenant-scoped persistent records. Monetary values are integer paise."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from qshift.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class Firm(Base):
    __tablename__ = "firms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    illustrative: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    demo_token_hash: Mapped[str] = mapped_column(String(64), unique=True)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    client_label: Mapped[str] = mapped_column(String(120))
    pinned_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RateCard(Base):
    __tablename__ = "rate_cards"
    __table_args__ = (UniqueConstraint("firm_id", "version", name="uq_firm_rate_card_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RateEntry(Base):
    __tablename__ = "rate_entries"
    __table_args__ = (UniqueConstraint("rate_card_id", "sku", name="uq_rate_card_sku"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    rate_card_id: Mapped[str] = mapped_column(ForeignKey("rate_cards.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(24))
    rate_paise: Mapped[int] = mapped_column(Integer)
    gst_bps: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("firm_id", "project_id", name="uq_firm_project_quote"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    rate_card_id: Mapped[str] = mapped_column(ForeignKey("rate_cards.id"))


class QuoteVersion(Base):
    __tablename__ = "quote_versions"
    __table_args__ = (UniqueConstraint("quote_id", "number", name="uq_quote_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    base_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_card_id: Mapped[str] = mapped_column(ForeignKey("rate_cards.id"))
    content_sha256: Mapped[str] = mapped_column(String(64))
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    total_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="APPROVED")
    change_summary: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (
        Index(
            "uq_project_open_draft",
            "firm_id",
            "project_id",
            unique=True,
            sqlite_where=text("status IN ('NEEDS_CLARIFICATION', 'DRAFT_READY')"),
            postgresql_where=text("status IN ('NEEDS_CLARIFICATION', 'DRAFT_READY')"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), index=True)
    base_version: Mapped[int] = mapped_column(Integer)
    rate_card_id: Mapped[str] = mapped_column(ForeignKey("rate_cards.id"))
    ops: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    total_paise: Mapped[int] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="NEEDS_CLARIFICATION")
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id"), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    approver_id: Mapped[str] = mapped_column(String(36))
    content_sha256: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuoteIntake(Base):
    __tablename__ = "quote_intakes"
    __table_args__ = (UniqueConstraint("firm_id", "project_id", name="uq_quote_intake_project"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    draft_id: Mapped[str | None] = mapped_column(ForeignKey("drafts.id"), nullable=True)
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    revision: Mapped[int] = mapped_column(Integer, default=1)

    __mapper_args__ = {"version_id_col": revision}


class SimulatedChat(Base):
    __tablename__ = "simulated_client_chats"
    __table_args__ = (UniqueConstraint("firm_id", "project_id", name="uq_sim_chat_project"),)

    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    rate_card_id: Mapped[str] = mapped_column(ForeignKey("rate_cards.id"))


class SimulatedReceipt(Base):
    __tablename__ = "simulated_client_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["firm_id", "chat_id"], ["simulated_client_chats.firm_id", "simulated_client_chats.id"]
        ),
    )

    firm_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    body_sha256: Mapped[str] = mapped_column(String(64))


class SimulatedQuoteDelivery(Base):
    __tablename__ = "simulated_quote_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["firm_id", "chat_id"], ["simulated_client_chats.firm_id", "simulated_client_chats.id"]
        ),
    )

    firm_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("quote_versions.id"), primary_key=True)
    quote_sha256: Mapped[str] = mapped_column(String(64))
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary)


class StudioProfile(Base):
    __tablename__ = "studio_profiles"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), unique=True)


class StudioCredential(Base):
    __tablename__ = "studio_credentials"

    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    password_hash: Mapped[str] = mapped_column(String(160))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudioSession(Base):
    __tablename__ = "studio_sessions"

    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str] = mapped_column(String(36))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
