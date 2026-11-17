"""Add tenant-scoped WhatsApp identities, events and outbound delivery state."""

import sqlalchemy as sa
from alembic import op

revision = "0012_whatsapp_identity_and_delivery"
down_revision = "0011_whatsapp_staff_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_business_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("provider_account_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("firm_id", "provider_account_id"),
    )
    op.create_table(
        "whatsapp_phone_numbers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("business_account_id", sa.String(36), sa.ForeignKey("whatsapp_business_accounts.id"), nullable=False),
        sa.Column("provider_phone_number_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.UniqueConstraint("provider_phone_number_id"),
    )
    op.create_table(
        "whatsapp_staff_enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("phone_number_id", sa.String(36), sa.ForeignKey("whatsapp_phone_numbers.id"), nullable=False),
        sa.Column("provider_sender_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("consent_reference", sa.String(64), nullable=True),
        sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("firm_id", "phone_number_id", "provider_sender_id"),
    )
    op.create_table(
        "customer_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("opt_in_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("firm_id", "phone_hash"),
    )
    op.create_table(
        "project_contact_associations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("customer_contacts.id"), nullable=False),
        sa.UniqueConstraint("firm_id", "project_id", "contact_id"),
    )
    op.create_table(
        "whatsapp_message_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("phone_number_id", sa.String(36), sa.ForeignKey("whatsapp_phone_numbers.id"), nullable=False),
        sa.Column("provider_message_id", sa.String(160), nullable=False),
        sa.Column("direction", sa.String(12), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("processing_state", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("firm_id", "provider_message_id"),
    )
    op.create_table(
        "whatsapp_outbound_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firm_id", sa.String(36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("provider_message_id", sa.String(160), nullable=True),
        sa.Column("recipient_hash", sa.String(64), nullable=False),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("quote_versions.id"), nullable=True),
        sa.Column("state", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("last_error", sa.String(240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("firm_id", "idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_outbound_deliveries")
    op.drop_table("whatsapp_message_events")
    op.drop_table("project_contact_associations")
    op.drop_table("customer_contacts")
    op.drop_table("whatsapp_staff_enrollments")
    op.drop_table("whatsapp_phone_numbers")
    op.drop_table("whatsapp_business_accounts")
