"""add company_type to companies

Revision ID: 20260908_company_type
Revises: 20260908_one_open_lot
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision = "20260908_company_type"
down_revision = "20260908_one_open_lot"
branch_labels = None
depends_on = None


def upgrade():
    company_type = ENUM("YARN_SPINNING", "GINNING", name="companytype", create_type=True)
    company_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "companies",
        sa.Column(
            "company_type",
            ENUM("YARN_SPINNING", "GINNING", name="companytype", create_type=False),
            nullable=False,
            server_default="YARN_SPINNING",
        ),
    )


def downgrade():
    op.drop_column("companies", "company_type")
    ENUM(name="companytype").drop(op.get_bind(), checkfirst=True)
