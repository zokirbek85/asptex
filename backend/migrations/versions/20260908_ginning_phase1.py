"""ginning phase 1: FARMER counterparty type, ginning_product_type dimension

Revision ID: 20260908_ginning_p1
Revises: 20260908_company_type
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision = "20260908_ginning_p1"
down_revision = "20260908_company_type"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE counterpartytype ADD VALUE IF NOT EXISTS 'FARMER'")

    ginning_product_type = ENUM(
        "FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER",
        name="ginningproducttype", create_type=True,
    )
    ginning_product_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "stock_transactions",
        sa.Column(
            "ginning_product_type",
            ENUM("FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER", name="ginningproducttype", create_type=False),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_st_ginning_balance",
        "stock_transactions",
        ["company_id", "warehouse_id", "ginning_product_type"],
    )


def downgrade():
    op.drop_index("idx_st_ginning_balance", table_name="stock_transactions")
    op.drop_column("stock_transactions", "ginning_product_type")
    ENUM(name="ginningproducttype").drop(op.get_bind(), checkfirst=True)
    # Note: Postgres cannot remove an enum value; FARMER stays in counterpartytype on downgrade.
