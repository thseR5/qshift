"""Add studio directory, credentials, and revocable sessions."""

import sqlalchemy as sa

from alembic import context, op

revision = "0007_studio_identity"
down_revision = "0006_simulated_client_bridge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    def missing(table: str) -> bool:
        return context.is_offline_mode() or not sa.inspect(op.get_bind()).has_table(table)

    if missing("studio_profiles"):
        op.create_table(
            "studio_profiles",
            sa.Column("slug", sa.String(64), primary_key=True),
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False, unique=True),
        )
    if missing("studio_credentials"):
        op.create_table(
            "studio_credentials",
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), primary_key=True),
            sa.Column("username", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(160), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), nullable=False),
            sa.Column("locked_until", sa.DateTime(timezone=True)),
        )
    if missing("studio_sessions"):
        op.create_table(
            "studio_sessions",
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), primary_key=True),
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("studio_sessions")
    op.drop_table("studio_credentials")
    op.drop_table("studio_profiles")
