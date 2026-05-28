"""add_tolling_module

Revision ID: 20260529_tolling
Revises: 20260529_opening_balance
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "20260529_tolling"
down_revision: Union[str, None] = "20260529_opening_balance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New ENUM types
    tolling_lot_status = ENUM("OPEN", "CLOSED", name="tollinglotstatus", create_type=True)
    tolling_lot_status.create(op.get_bind(), checkfirst=True)

    tolling_dist_status = ENUM("DRAFT", "CONFIRMED", name="tollingdistributionstatus", create_type=True)
    tolling_dist_status.create(op.get_bind(), checkfirst=True)

    tolling_line_type = ENUM("OWNER_NET", "PROCESSOR_FEE", name="tollinglinetype", create_type=True)
    tolling_line_type.create(op.get_bind(), checkfirst=True)

    # Add new TransactionType values to existing enum
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'TOLLING_OWNER_INBOUND'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'TOLLING_FEE_INBOUND'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'TOLLING_RAW_RECEIPT'")

    # tolling_lots
    op.create_table(
        "tolling_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id"), nullable=False, unique=True),
        sa.Column("status", ENUM("OPEN", "CLOSED", name="tollinglotstatus", create_type=False), nullable=False, server_default="OPEN"),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tolling_lots_company", "tolling_lots", ["company_id"])

    # tolling_lot_participants
    op.create_table(
        "tolling_lot_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tolling_lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("raw_kg_delivered", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("fee_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("fee_currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("fee_rate_per_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tolling_lot_id", "counterparty_id", name="uq_tolling_participant_lot_cp"),
    )
    op.create_index("ix_tolling_participants_lot", "tolling_lot_participants", ["tolling_lot_id"])

    # tolling_daily_distributions
    op.create_table(
        "tolling_daily_distributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tolling_lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_lots.id"), nullable=False),
        sa.Column("distribution_date", sa.Date, nullable=False),
        sa.Column("daily_fg_kg_total", sa.Numeric(15, 3), nullable=False),
        sa.Column("status", ENUM("DRAFT", "CONFIRMED", name="tollingdistributionstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tolling_lot_id", "distribution_date", name="uq_tolling_dist_lot_date"),
    )
    op.create_index("ix_tolling_dist_company", "tolling_daily_distributions", ["company_id"])
    op.create_index("ix_tolling_dist_lot", "tolling_daily_distributions", ["tolling_lot_id"])

    # tolling_daily_raw_intakes
    op.create_table(
        "tolling_daily_raw_intakes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("distribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_daily_distributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_lot_participants.id"), nullable=False),
        sa.Column("raw_kg_received_today", sa.Numeric(15, 3), nullable=False, server_default="0"),
    )
    op.create_index("ix_tolling_raw_intakes_dist", "tolling_daily_raw_intakes", ["distribution_id"])

    # tolling_distribution_lines
    op.create_table(
        "tolling_distribution_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("distribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_daily_distributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tolling_lot_participants.id"), nullable=True),
        sa.Column("line_type", ENUM("OWNER_NET", "PROCESSOR_FEE", name="tollinglinetype", create_type=False), nullable=False),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=True),
        sa.Column("gross_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("fee_kg", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("net_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("ownership_share_pct", sa.Numeric(8, 5), nullable=False),
        sa.Column("fee_pct_applied", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("fee_amount_uzs", sa.Numeric(18, 2), nullable=True),
        sa.Column("fee_amount_usd", sa.Numeric(18, 4), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(18, 4), nullable=True),
        sa.Column("stock_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tolling_dist_lines_dist", "tolling_distribution_lines", ["distribution_id"])


def downgrade() -> None:
    op.drop_index("ix_tolling_dist_lines_dist", table_name="tolling_distribution_lines")
    op.drop_table("tolling_distribution_lines")
    op.drop_index("ix_tolling_raw_intakes_dist", table_name="tolling_daily_raw_intakes")
    op.drop_table("tolling_daily_raw_intakes")
    op.drop_index("ix_tolling_dist_lot", table_name="tolling_daily_distributions")
    op.drop_index("ix_tolling_dist_company", table_name="tolling_daily_distributions")
    op.drop_table("tolling_daily_distributions")
    op.drop_index("ix_tolling_participants_lot", table_name="tolling_lot_participants")
    op.drop_table("tolling_lot_participants")
    op.drop_index("ix_tolling_lots_company", table_name="tolling_lots")
    op.drop_table("tolling_lots")
    op.execute("DROP TYPE IF EXISTS tollinglinetype")
    op.execute("DROP TYPE IF EXISTS tollingdistributionstatus")
    op.execute("DROP TYPE IF EXISTS tollinglotstatus")
