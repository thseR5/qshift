"""Persist signed pilot messages until the worker can process them."""

import sqlalchemy as sa

from alembic import op

revision = "0009_pilot_inbox"
down_revision = "0008_pilot_document"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_receipts", sa.Column("inbound_text", sa.Text()))


def downgrade() -> None:
    op.drop_column("whatsapp_receipts", "inbound_text")
