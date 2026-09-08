"""ginning phase 6: exchange sales

Revision ID: 20260908_ginning_p6
Revises: 20260908_ginning_p5
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p6"
down_revision = "20260908_ginning_p5"
branch_labels = None
depends_on = None


def upgrade():
    sale_status = ENUM("ACTIVE", "PARTIALLY_CANCELLED", "CANCELLED", name="exchangesalestatus", create_type=True)
    sale_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "exchange_sales",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("sale_number", sa.String(30), nullable=False),
        sa.Column("sale_date", sa.Date, nullable=False),
        sa.Column("status", ENUM("ACTIVE", "PARTIALLY_CANCELLED", "CANCELLED", name="exchangesalestatus", create_type=False), nullable=False, server_default="ACTIVE"),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("exchange_name", sa.String(100), nullable=True),
        sa.Column("exchange_lot_number", sa.String(50), nullable=True),
        sa.Column("commission_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("broker_name", sa.String(150), nullable=True),
        sa.Column("transport_cost", sa.Numeric(18, 2), nullable=True),
        sa.Column("other_costs", sa.Numeric(18, 2), nullable=True),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="UNPAID"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "sale_number", name="uq_exchange_sale_company_number"),
    )
    op.create_index("ix_exchange_sales_company_id", "exchange_sales", ["company_id"])
    op.create_index("ix_exchange_sales_warehouse_id", "exchange_sales", ["warehouse_id"])
    op.create_index("ix_exchange_sales_customer_id", "exchange_sales", ["customer_id"])
    op.create_index("ix_exchange_sales_sale_date", "exchange_sales", ["sale_date"])

    op.create_table(
        "exchange_sale_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sale_id", UUID(as_uuid=True), sa.ForeignKey("exchange_sales.id"), nullable=False),
        sa.Column("product_type", ENUM("FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER", name="ginningproducttype", create_type=False), nullable=False),
        sa.Column("bale_id", UUID(as_uuid=True), sa.ForeignKey("ginning_bales.id"), nullable=True),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("cancelled_kg", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("is_fully_cancelled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("line_number", sa.SmallInteger, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("sale_id", "line_number", name="uq_esl_sale_line"),
        sa.CheckConstraint("quantity_kg > 0", name="chk_esl_qty_positive"),
    )
    op.create_index("ix_exchange_sale_lines_sale_id", "exchange_sale_lines", ["sale_id"])

    op.create_table(
        "exchange_sale_cancellations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sale_id", UUID(as_uuid=True), sa.ForeignKey("exchange_sales.id"), nullable=False),
        sa.Column("sale_line_id", UUID(as_uuid=True), sa.ForeignKey("exchange_sale_lines.id"), nullable=True),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("reversal_transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity_kg > 0", name="chk_esc_qty_positive"),
    )
    op.create_index("ix_exchange_sale_cancellations_sale_id", "exchange_sale_cancellations", ["sale_id"])

    op.create_table(
        "exchange_sale_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("exchange_sale_number_sequences")
    op.drop_table("exchange_sale_cancellations")
    op.drop_table("exchange_sale_lines")
    op.drop_table("exchange_sales")
    ENUM(name="exchangesalestatus").drop(op.get_bind(), checkfirst=True)
