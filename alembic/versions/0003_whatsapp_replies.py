"""Record reply attempts and staff opt-outs for the WhatsApp test pilot."""

import sqlalchemy as sa
from alembic import op

revision = "0003_whatsapp_replies"
down_revision = "0002_whatsapp_receive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_conversations",
        sa.Column("delivery_opted_out", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "whatsapp_receipts",
        sa.Column("source_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "whatsapp_receipts",
        sa.Column("delivery_state", sa.String(20), nullable=False, server_default="captured"),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_receipts", "delivery_state")
    op.drop_column("whatsapp_receipts", "source_sent_at")
    op.drop_column("whatsapp_conversations", "delivery_opted_out")
