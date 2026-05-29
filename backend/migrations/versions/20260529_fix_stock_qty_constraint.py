"""fix stock_transactions qty constraint to allow units-only rows

Revision ID: 20260529_fix_qty
Revises: 20260529_add_tolling_module
Create Date: 2026-05-29

"""
from alembic import op

revision = "20260529_fix_qty"
down_revision = "20260529_tolling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("chk_qty_positive", "stock_transactions")
    op.create_check_constraint(
        "chk_qty_positive",
        "stock_transactions",
        "quantity_kg > 0 OR COALESCE(quantity_units, 0) > 0",
    )


def downgrade() -> None:
    op.drop_constraint("chk_qty_positive", "stock_transactions")
    op.create_check_constraint(
        "chk_qty_positive",
        "stock_transactions",
        "quantity_kg > 0",
    )
