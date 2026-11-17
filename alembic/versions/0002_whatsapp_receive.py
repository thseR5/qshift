"""Persist WhatsApp pilot conversations and receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0002_whatsapp_receive"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_conversations",
        sa.Column("firm_id", sa.String(36), primary_key=True),
        sa.Column("enrollment_key", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("draft_id", sa.String(36), nullable=True),
    )
    op.create_table(
        "whatsapp_receipts",
        sa.Column("firm_id", sa.String(36), primary_key=True),
        sa.Column("enrollment_key", sa.String(64), primary_key=True),
        sa.Column("message_hash", sa.String(64), primary_key=True),
        sa.Column("reply", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["firm_id", "enrollment_key"],
            ["whatsapp_conversations.firm_id", "whatsapp_conversations.enrollment_key"],
            name="fk_whatsapp_receipt_conversation",
        ),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_receipts")
    op.drop_table("whatsapp_conversations")
