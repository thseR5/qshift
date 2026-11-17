"""Add inbox receipts and exact-PDF delivery for simulated client chats."""

import sqlalchemy as sa

from alembic import context, op

revision = "0006_simulated_client_bridge"
down_revision = "0005_quote_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    def missing(table: str) -> bool:
        return context.is_offline_mode() or not sa.inspect(op.get_bind()).has_table(table)

    if missing("simulated_client_chats"):
        op.create_table(
            "simulated_client_chats",
            sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), primary_key=True),
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("rate_card_id", sa.String(36), sa.ForeignKey("rate_cards.id"), nullable=False),
            sa.UniqueConstraint("firm_id", "project_id", name="uq_sim_chat_project"),
        )
    if missing("simulated_client_receipts"):
        op.create_table(
            "simulated_client_receipts",
            sa.Column("firm_id", sa.String(36), primary_key=True),
            sa.Column("chat_id", sa.String(36), primary_key=True),
            sa.Column("event_id", sa.String(80), primary_key=True),
            sa.Column("body_sha256", sa.String(64), nullable=False),
            sa.ForeignKeyConstraint(
                ["firm_id", "chat_id"],
                ["simulated_client_chats.firm_id", "simulated_client_chats.id"],
            ),
        )
    if missing("simulated_quote_deliveries"):
        op.create_table(
            "simulated_quote_deliveries",
            sa.Column("firm_id", sa.String(36), primary_key=True),
            sa.Column("chat_id", sa.String(36), primary_key=True),
            sa.Column(
                "version_id", sa.String(36), sa.ForeignKey("quote_versions.id"), primary_key=True
            ),
            sa.Column("quote_sha256", sa.String(64), nullable=False),
            sa.Column("pdf_sha256", sa.String(64), nullable=False),
            sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
            sa.ForeignKeyConstraint(
                ["firm_id", "chat_id"],
                ["simulated_client_chats.firm_id", "simulated_client_chats.id"],
            ),
        )


def downgrade() -> None:
    op.drop_table("simulated_quote_deliveries")
    op.drop_table("simulated_client_receipts")
    op.drop_table("simulated_client_chats")
