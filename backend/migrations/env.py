import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Import all models so Alembic can detect them ─────────────────────────────
from app.shared.base_model import Base  # noqa: F401

# Core models
from app.modules.auth.models import User, RefreshToken  # noqa: F401
from app.modules.company.models import Company  # noqa: F401
from app.modules.user.models import UserCompanyRole  # noqa: F401
from app.modules.warehouse.models import Warehouse  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.counterparty.models import Counterparty, CounterpartyContact  # noqa: F401
from app.modules.contract.models import Contract  # noqa: F401
from app.modules.count_catalog.models import CountCatalog  # noqa: F401
from app.modules.lot.models import Lot, LotNumberSequence  # noqa: F401
from app.modules.stock.models import StockTransaction  # noqa: F401
from app.modules.daily_report.models import DailyReport, DailyReportLine  # noqa: F401
from app.modules.shipment.models import (  # noqa: F401
    Shipment, ShipmentLine, ShipmentCancellation, ShipmentNumberSequence
)
from app.modules.adjustment.models import (  # noqa: F401
    InventoryAdjustment, InventoryAdjustmentLine, AdjustmentNumberSequence
)

config = context.config

# Override sqlalchemy.url from environment variable if set
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Alembic requires non-async URL for sync operations in some contexts;
    # but we use async engine below so keep asyncpg driver.
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
