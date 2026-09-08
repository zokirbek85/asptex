"""ginning phase 5: intercompany transfer (ginning -> spinning)

Revision ID: 20260908_ginning_p5
Revises: 20260908_ginning_p4
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p5"
down_revision = "20260908_ginning_p4"
branch_labels = None
depends_on = None


def upgrade():
    transfer_status = ENUM("DRAFT", "CONFIRMED", "CANCELLED", name="intercompanytransferstatus", create_type=True)
    transfer_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "intercompany_transfers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("destination_company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("destination_warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("product_type", ENUM("FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER", name="ginningproducttype", create_type=False), nullable=False),
        sa.Column("transfer_number", sa.String(30), nullable=False),
        sa.Column("transfer_date", sa.Date, nullable=False),
        sa.Column("status", ENUM("DRAFT", "CONFIRMED", "CANCELLED", name="intercompanytransferstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("total_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("total_quantity_kg", sa.Numeric(15, 3), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_intercompany_transfers_source_company_id", "intercompany_transfers", ["source_company_id"])
    op.create_index("ix_intercompany_transfers_destination_company_id", "intercompany_transfers", ["destination_company_id"])
    op.create_index("ix_intercompany_transfers_transfer_date", "intercompany_transfers", ["transfer_date"])

    op.create_table(
        "intercompany_transfer_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("transfer_id", UUID(as_uuid=True), sa.ForeignKey("intercompany_transfers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bale_id", UUID(as_uuid=True), sa.ForeignKey("ginning_bales.id"), nullable=True),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("source_transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("destination_transaction_id", UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("quantity_kg > 0", name="chk_itl_qty_positive"),
    )
    op.create_index("ix_intercompany_transfer_lines_transfer_id", "intercompany_transfer_lines", ["transfer_id"])

    op.create_table(
        "intercompany_transfer_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("intercompany_transfer_number_sequences")
    op.drop_table("intercompany_transfer_lines")
    op.drop_table("intercompany_transfers")
    ENUM(name="intercompanytransferstatus").drop(op.get_bind(), checkfirst=True)
