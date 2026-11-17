"""Track the one allowed first-quote PDF attempt for a pilot enrollment."""

import sqlalchemy as sa

from alembic import op

revision = "0008_pilot_document"
down_revision = "0007_studio_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_conversations", sa.Column("document_state", sa.String(20)))


def downgrade() -> None:
    op.drop_column("whatsapp_conversations", "document_state")
