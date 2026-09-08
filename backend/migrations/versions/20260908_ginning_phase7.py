"""ginning phase 7: farmer payments

Revision ID: 20260908_ginning_p7
Revises: 20260908_ginning_p6
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p7"
down_revision = "20260908_ginning_p6"
branch_labels = None
depends_on = None


def upgrade():
    payment_status = ENUM("DRAFT", "POSTED", "CANCELLED", name="farmerpaymentstatus", create_type=True)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "farmer_payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("farmer_id", UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False),
        sa.Column("payment_number", sa.String(30), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("payment_method", sa.String(20), nullable=False, server_default="CASH"),
        sa.Column("status", ENUM("DRAFT", "POSTED", "CANCELLED", name="farmerpaymentstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("ledger_entry_id", UUID(as_uuid=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("farmer_name", sa.String(255), nullable=True),
        sa.Column("reference_note", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "payment_number", name="uq_farmer_payment_company_number"),
        sa.CheckConstraint("amount > 0", name="chk_fp_amount_positive"),
    )
    op.create_index("ix_farmer_payments_company_id", "farmer_payments", ["company_id"])
    op.create_index("ix_farmer_payments_farmer_id", "farmer_payments", ["farmer_id"])
    op.create_index("ix_farmer_payments_payment_date", "farmer_payments", ["payment_date"])

    op.create_table(
        "farmer_payment_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("farmer_payment_number_sequences")
    op.drop_table("farmer_payments")
    ENUM(name="farmerpaymentstatus").drop(op.get_bind(), checkfirst=True)
