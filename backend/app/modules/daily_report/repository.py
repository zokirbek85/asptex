from datetime import date, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.daily_report.models import DailyReport, DailyReportLine
from app.shared.base_repository import BaseRepository
from app.shared.enums import ReportStatus


class DailyReportRepository(BaseRepository[DailyReport]):
    model = DailyReport

    async def get_by_warehouse_date(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        report_date: date,
    ) -> DailyReport | None:
        result = await self.session.execute(
            select(DailyReport).where(
                DailyReport.company_id == company_id,
                DailyReport.warehouse_id == warehouse_id,
                DailyReport.report_date == report_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_previous_day_report(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        report_date: date,
    ) -> DailyReport | None:
        prev = report_date - timedelta(days=1)
        return await self.get_by_warehouse_date(company_id, warehouse_id, prev)

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None,
        page: int,
        page_size: int,
        status: ReportStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[DailyReport], int]:
        conditions = [DailyReport.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(DailyReport.warehouse_id == warehouse_id)
        if status is not None:
            conditions.append(DailyReport.status == status)
        if date_from is not None:
            conditions.append(DailyReport.report_date >= date_from)
        if date_to is not None:
            conditions.append(DailyReport.report_date <= date_to)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(DailyReport)
            .where(*conditions)
            .order_by(DailyReport.report_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_with_lines(self, report_id: uuid.UUID) -> DailyReport | None:
        result = await self.session.execute(
            select(DailyReport)
            .options(selectinload(DailyReport.lines))
            .where(DailyReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def replace_lines(
        self,
        report: DailyReport,
        lines_data: list[dict],
    ) -> DailyReport:
        """Delete all existing lines and insert new ones."""
        for line in list(report.lines):
            await self.session.delete(line)
        await self.session.flush()

        for idx, ld in enumerate(lines_data, start=1):
            line = DailyReportLine(
                daily_report_id=report.id,
                line_number=idx,
                **ld,
            )
            self.session.add(line)

        await self.session.flush()
        await self.session.refresh(report)
        return report
