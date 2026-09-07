import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError
from app.modules.daily_report.models import DailyReport
from app.shared.enums import ReportStatus


async def assert_open_period(
    session: AsyncSession,
    company_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    tx_date: date,
) -> None:
    """Blocks posting a stock transaction into a warehouse/date whose daily
    report has already been CLOSED — a closed report is reconciled and must
    not silently drift out of sync with the ledger."""
    result = await session.execute(
        select(DailyReport.status).where(
            DailyReport.company_id == company_id,
            DailyReport.warehouse_id == warehouse_id,
            DailyReport.report_date == tx_date,
        )
    )
    status = result.scalar_one_or_none()
    if status == ReportStatus.CLOSED:
        raise BusinessRuleViolationError(
            f"{tx_date} davri yopilgan — posting mumkin emas", code="PERIOD_LOCKED"
        )
