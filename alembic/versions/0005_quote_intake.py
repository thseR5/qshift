"""Persist simulated first-quote conversations."""

import sqlalchemy as sa

from alembic import context, op

revision = "0005_quote_intake"
down_revision = "0004_whatsapp_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Local demo startup can create the identical ORM table before make migrate.
    if not context.is_offline_mode() and sa.inspect(op.get_bind()).has_table("quote_intakes"):
        return
    op.create_table(
        "quote_intakes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("draft_id", sa.String(36), sa.ForeignKey("drafts.id"), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("firm_id", "project_id", name="uq_quote_intake_project"),
    )
    op.create_index("ix_quote_intakes_firm_id", "quote_intakes", ["firm_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_intakes_firm_id", table_name="quote_intakes")
    op.drop_table("quote_intakes")
