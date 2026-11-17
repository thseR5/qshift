"""Store firm-specific catalogue aliases for deterministic matching."""

import sqlalchemy as sa

from alembic import op

revision = "0010_rate_entry_aliases"
down_revision = "0009_pilot_inbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("rate_entries")}
    if "aliases" not in columns:
        op.add_column("rate_entries", sa.Column("aliases", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("rate_entries", "aliases")
