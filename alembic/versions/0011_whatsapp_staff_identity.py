"""Bind WhatsApp enrollments to a tenant-scoped staff identity and pending PDF version."""

import sqlalchemy as sa
from alembic import op

revision = "0011_whatsapp_staff_identity"
down_revision = "0010_rate_entry_aliases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_conversations", sa.Column("user_id", sa.String(36), nullable=True))
    op.add_column(
        "whatsapp_conversations", sa.Column("pending_version_id", sa.String(36), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("whatsapp_conversations", "pending_version_id")
    op.drop_column("whatsapp_conversations", "user_id")
