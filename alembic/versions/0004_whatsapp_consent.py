"""Require fresh, documented consent before processing pilot chats."""

import sqlalchemy as sa

from alembic import op

revision = "0004_whatsapp_consent"
down_revision = "0003_whatsapp_replies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_conversations", sa.Column("consent_reference", sa.String(64)))
    op.add_column(
        "whatsapp_conversations", sa.Column("consent_recorded_at", sa.DateTime(timezone=True))
    )
    receipts = sa.table("whatsapp_receipts", sa.column("delivery_state", sa.String()))
    op.execute(
        receipts.update()
        .where(receipts.c.delivery_state == "ready")
        .values(delivery_state="suppressed")
    )


def downgrade() -> None:
    op.drop_column("whatsapp_conversations", "consent_recorded_at")
    op.drop_column("whatsapp_conversations", "consent_reference")
