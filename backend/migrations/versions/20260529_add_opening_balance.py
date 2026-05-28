"""add_opening_balance_tables

Revision ID: 20260529_opening_balance
Revises: 55b9d1537055
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "20260529_opening_balance"
down_revision: Union[str, None] = "55b9d1537055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opening_balance_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("balance_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            ENUM("DRAFT", "POSTED", name="adjustmentstatus", create_type=False),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "warehouse_id", "balance_date", name="uq_ob_company_warehouse_date"),
    )
    op.create_index("ix_ob_entries_company", "opening_balance_entries", ["company_id"])
    op.create_index("ix_ob_entries_warehouse", "opening_balance_entries", ["warehouse_id"])

    op.create_table(
        "opening_balance_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opening_balance_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id"), nullable=True),
        sa.Column("count_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("count_catalog.id"), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=True),
        sa.Column(
            "waste_type",
            ENUM("ST_3", "ST_7_11", "ST_1", "ST_36", "ST_98", "MYCHKA", "ROVNITSA", name="wastetype", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "pkg_item_type",
            ENUM("BAG", "CONE", "PACKAGE", "CORRUGATED_SHEET", "PARAFFIN", "BOX", name="packagingitemtype", create_type=False),
            nullable=True,
        ),
        sa.Column("quantity_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("quantity_bags", sa.Integer, nullable=True),
        sa.Column("quantity_kip", sa.Numeric(15, 3), nullable=True),
        sa.Column("quantity_units", sa.Integer, nullable=True),
        sa.Column("lot_number", sa.String(20), nullable=True),
        sa.Column("count_value", sa.String(50), nullable=True),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("line_number", sa.SmallInteger, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ob_lines_entry", "opening_balance_lines", ["entry_id"])


def downgrade() -> None:
    op.drop_index("ix_ob_lines_entry", table_name="opening_balance_lines")
    op.drop_table("opening_balance_lines")
    op.drop_index("ix_ob_entries_warehouse", table_name="opening_balance_entries")
    op.drop_index("ix_ob_entries_company", table_name="opening_balance_entries")
    op.drop_table("opening_balance_entries")
