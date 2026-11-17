"""Persistent state for the staff-only WhatsApp pilot."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKeyConstraint, String, Text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from qshift.models import now_utc


class WhatsAppBase(DeclarativeBase):
    pass


class Conversation(WhatsAppBase):
    __tablename__ = "whatsapp_conversations"

    firm_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    enrollment_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(36))
    draft_id: Mapped[str | None] = mapped_column(String(36))
    delivery_opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_reference: Mapped[str | None] = mapped_column(String(64))
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_state: Mapped[str | None] = mapped_column(String(20))

    def consent_start(self) -> datetime | None:
        recorded = self.consent_recorded_at
        if not self.consent_reference or recorded is None:
            return None
        return recorded.replace(tzinfo=UTC) if recorded.tzinfo is None else recorded.astimezone(UTC)

    def has_active_consent(self, now: datetime) -> bool:
        start = self.consent_start()
        return (
            not self.delivery_opted_out
            and start is not None
            and start <= now < start + timedelta(hours=24)
        )


class Receipt(WhatsAppBase):
    __tablename__ = "whatsapp_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["firm_id", "enrollment_key"],
            ["whatsapp_conversations.firm_id", "whatsapp_conversations.enrollment_key"],
            name="fk_whatsapp_receipt_conversation",
        ),
    )

    firm_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    enrollment_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    reply: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    source_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_state: Mapped[str] = mapped_column(String(20), default="captured")
    inbound_text: Mapped[str | None] = mapped_column(Text)


def lock_conversation(session: Session, identity: tuple[str, str]) -> Conversation | None:
    if session.get_bind().dialect.name == "postgresql":
        return session.get(Conversation, identity, with_for_update=True)

    # Begin a SQLite write transaction before reading the enrollment.
    session.execute(
        update(Conversation)
        .where(Conversation.firm_id == identity[0], Conversation.enrollment_key == identity[1])
        .values(enrollment_key=Conversation.enrollment_key)
    )
    return session.get(Conversation, identity)
