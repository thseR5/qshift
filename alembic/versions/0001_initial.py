"""Create initial Qshift tables."""
from alembic import op

from qshift.db import Base
import qshift.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# Freeze the table set so future ORM models are created by their own migrations.
INITIAL_TABLES = (
    "firms", "users", "projects", "rate_cards", "rate_entries", "quotes",
    "quote_versions", "drafts", "approvals", "audit_events",
)


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in INITIAL_TABLES]
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in INITIAL_TABLES]
    )

