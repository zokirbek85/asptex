import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.adjustment.models import AdjustmentNumberSequence, InventoryAdjustment
from app.modules.audit.service import AuditService
from app.modules.company.models import Company
from app.modules.daily_report.models import DailyReport
from app.modules.data_reset.schemas import DATA_RESET_MODULES, DataResetResponse
from app.modules.lot.models import Lot, LotNumberSequence
from app.modules.opening_balance.models import OpeningBalanceEntry
from app.modules.shipment.models import (
    Shipment,
    ShipmentCancellation,
    ShipmentLine,
    ShipmentNumberSequence,
)
from app.modules.stock.models import StockTransaction
from app.modules.tolling.models import TollingDistribution, TollingLot
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction

# A module that deletes a "lots"-referencing table must run before "lots" itself,
# and "shipments" must run before "daily_reports" (shipments.daily_report_id → daily_reports).
# Selecting a module on the right auto-includes the modules on the left.
_DEPENDENCIES: dict[str, list[str]] = {
    "daily_reports": ["shipments"],
    "lots": ["tolling", "shipments", "adjustments", "opening_balance", "daily_reports", "stock_transactions"],
}


class DataResetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def reset(
        self,
        company_id: uuid.UUID,
        modules: list[str],
        confirm_company_name: str,
        ctx: AuditContext,
    ) -> DataResetResponse:
        company = await self.session.get(Company, company_id)
        if company is None:
            raise NotFoundError("Company", company_id)

        if confirm_company_name.strip() != company.name:
            raise BusinessRuleViolationError(
                "Tasdiqlash matni kompaniya nomiga mos emas", "CONFIRMATION_MISMATCH"
            )

        invalid = set(modules) - set(DATA_RESET_MODULES)
        if invalid:
            raise BusinessRuleViolationError(f"Noma'lum modul(lar): {', '.join(sorted(invalid))}")

        selected = set(modules)
        changed = True
        while changed:
            changed = False
            for m in list(selected):
                for dep in _DEPENDENCIES.get(m, []):
                    if dep not in selected:
                        selected.add(dep)
                        changed = True
        ordered = [m for m in DATA_RESET_MODULES if m in selected]

        counts: dict[str, int] = {}

        if "tolling" in ordered:
            counts["tolling_daily_distributions"] = await self._delete(
                TollingDistribution, TollingDistribution.company_id == company_id
            )
            counts["tolling_lots"] = await self._delete(TollingLot, TollingLot.company_id == company_id)

        if "shipments" in ordered:
            shipment_ids = select(Shipment.id).where(Shipment.company_id == company_id)
            counts["shipment_cancellations"] = await self._delete(
                ShipmentCancellation, ShipmentCancellation.shipment_id.in_(shipment_ids)
            )
            counts["shipment_lines"] = await self._delete(
                ShipmentLine, ShipmentLine.shipment_id.in_(shipment_ids)
            )
            counts["shipments"] = await self._delete(Shipment, Shipment.company_id == company_id)
            counts["shipment_number_sequences"] = await self._delete(
                ShipmentNumberSequence, ShipmentNumberSequence.company_id == company_id
            )

        if "adjustments" in ordered:
            counts["inventory_adjustments"] = await self._delete(
                InventoryAdjustment, InventoryAdjustment.company_id == company_id
            )
            counts["adjustment_number_sequences"] = await self._delete(
                AdjustmentNumberSequence, AdjustmentNumberSequence.company_id == company_id
            )

        if "opening_balance" in ordered:
            counts["opening_balance_entries"] = await self._delete(
                OpeningBalanceEntry, OpeningBalanceEntry.company_id == company_id
            )

        if "daily_reports" in ordered:
            counts["daily_reports"] = await self._delete(DailyReport, DailyReport.company_id == company_id)

        if "stock_transactions" in ordered:
            counts["stock_transactions"] = await self._delete(
                StockTransaction, StockTransaction.company_id == company_id
            )

        if "lots" in ordered:
            counts["lots"] = await self._delete(Lot, Lot.company_id == company_id)
            counts["lot_number_sequences"] = await self._delete(
                LotNumberSequence, LotNumberSequence.company_id == company_id
            )

        await AuditService(self.session).log(
            ctx=ctx,
            entity_type="DataReset",
            action=AuditAction.DELETE,
            entity_display=", ".join(ordered),
            after_data=counts,
            reason=f"Admin data reset: {', '.join(ordered)}",
        )

        return DataResetResponse(modules_cleared=ordered, deleted_counts=counts)

    async def _delete(self, model, condition) -> int:
        result = await self.session.execute(delete(model).where(condition))
        return result.rowcount or 0
