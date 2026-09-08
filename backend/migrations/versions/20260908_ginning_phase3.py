"""ginning phase 3: production orders (multi-bunt input, multi-product output)

Revision ID: 20260908_ginning_p3
Revises: 20260908_ginning_p2
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p3"
down_revision = "20260908_ginning_p2"
branch_labels = None
depends_on = None


def upgrade():
    prod_status = ENUM("DRAFT", "COMPLETED", "CANCELLED", name="ginningproductionstatus", create_type=True)
    prod_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ginning_production_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("production_number", sa.String(30), nullable=False),
        sa.Column("production_date", sa.Date, nullable=False),
        sa.Column("status", ENUM("DRAFT", "COMPLETED", "CANCELLED", name="ginningproductionstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("total_input_kg", sa.Numeric(15, 3), nullable=True),
        sa.Column("total_output_kg", sa.Numeric(15, 3), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ginning_production_orders_company_id", "ginning_production_orders", ["company_id"])
    op.create_index("ix_ginning_production_orders_production_date", "ginning_production_orders", ["production_date"])

    op.create_table(
        "ginning_production_inputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("ginning_production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bunt_id", UUID(as_uuid=True), sa.ForeignKey("ginning_bunts.id"), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("transaction_id", UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("quantity_kg > 0", name="chk_gpi_qty_positive"),
    )
    op.create_index("ix_ginning_production_inputs_order_id", "ginning_production_inputs", ["order_id"])

    op.create_table(
        "ginning_production_outputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("ginning_production_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_type", ENUM("FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER", name="ginningproducttype", create_type=False), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint("quantity_kg > 0", name="chk_gpo_qty_positive"),
    )
    op.create_index("ix_ginning_production_outputs_order_id", "ginning_production_outputs", ["order_id"])

    op.create_table(
        "ginning_production_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("ginning_production_number_sequences")
    op.drop_table("ginning_production_outputs")
    op.drop_table("ginning_production_inputs")
    op.drop_table("ginning_production_orders")
    ENUM(name="ginningproductionstatus").drop(op.get_bind(), checkfirst=True)
