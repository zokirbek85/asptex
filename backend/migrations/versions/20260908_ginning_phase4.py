"""ginning phase 4: bale management

Revision ID: 20260908_ginning_p4
Revises: 20260908_ginning_p3
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p4"
down_revision = "20260908_ginning_p3"
branch_labels = None
depends_on = None


def upgrade():
    bale_status = ENUM("IN_STOCK", "SOLD", "TRANSFERRED", name="ginningbalestatus", create_type=True)
    bale_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ginning_bales",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("ginning_production_orders.id"), nullable=False),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("bale_number", sa.String(30), nullable=False),
        sa.Column("production_date", sa.Date, nullable=False),
        sa.Column("gross_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("tare_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("net_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("moisture_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("micronaire", sa.Numeric(5, 2), nullable=True),
        sa.Column("staple_length_mm", sa.Numeric(5, 2), nullable=True),
        sa.Column("strength", sa.Numeric(6, 2), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("trash_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("quality_class", sa.String(20), nullable=True),
        sa.Column("status", ENUM("IN_STOCK", "SOLD", "TRANSFERRED", name="ginningbalestatus", create_type=False), nullable=False, server_default="IN_STOCK"),
        sa.Column("sold_reference_type", sa.String(50), nullable=True),
        sa.Column("sold_reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "bale_number", name="uq_ginning_bale_company_number"),
        sa.CheckConstraint("gross_weight_kg > tare_weight_kg", name="chk_gb_gross_gt_tare"),
        sa.CheckConstraint("net_weight_kg > 0", name="chk_gb_net_positive"),
    )
    op.create_index("ix_ginning_bales_company_id", "ginning_bales", ["company_id"])
    op.create_index("ix_ginning_bales_production_order_id", "ginning_bales", ["production_order_id"])
    op.create_index("ix_ginning_bales_production_date", "ginning_bales", ["production_date"])

    op.create_table(
        "ginning_bale_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("ginning_bale_number_sequences")
    op.drop_table("ginning_bales")
    ENUM(name="ginningbalestatus").drop(op.get_bind(), checkfirst=True)
