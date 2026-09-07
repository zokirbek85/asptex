"""partial unique index: one open tolling lot per company

Revision ID: 20260908_one_open_lot
Revises: 20260529_fix_qty
Create Date: 2026-09-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260908_one_open_lot'
down_revision = '20260529_fix_qty'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'uq_one_open_tolling_lot',
        'tolling_lots',
        ['company_id'],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade():
    op.drop_index('uq_one_open_tolling_lot', table_name='tolling_lots')
