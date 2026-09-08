"""ginning phase 8: production costing

Revision ID: 20260908_ginning_p8
Revises: 20260908_ginning_p7
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p8"
down_revision = "20260908_ginning_p7"
branch_labels = None
depends_on = None


def upgrade():
    cost_type = ENUM(
        "RAW_MATERIAL", "ELECTRICITY", "GAS", "LABOR", "DEPRECIATION",
        "MAINTENANCE", "PACKAGING", "OVERHEAD", "OTHER",
        name="ginningcosttype", create_type=True,
    )
    cost_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ginning_production_costs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("production_order_id", UUID(as_uuid=True), sa.ForeignKey("ginning_production_orders.id"), nullable=False),
        sa.Column("cost_type", ENUM(
            "RAW_MATERIAL", "ELECTRICITY", "GAS", "LABOR", "DEPRECIATION",
            "MAINTENANCE", "PACKAGING", "OVERHEAD", "OTHER",
            name="ginningcosttype", create_type=False,
        ), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="chk_gpc_amount_positive"),
        sa.CheckConstraint("cost_type != 'RAW_MATERIAL'", name="chk_gpc_no_raw_material"),
    )
    op.create_index("ix_ginning_production_costs_company_id", "ginning_production_costs", ["company_id"])
    op.create_index("ix_ginning_production_costs_production_order_id", "ginning_production_costs", ["production_order_id"])


def downgrade():
    op.drop_table("ginning_production_costs")
    ENUM(name="ginningcosttype").drop(op.get_bind(), checkfirst=True)
