from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.cotton_receiving.repository import CottonReceivingRepository
from app.modules.exchange_sale.models import ExchangeSale, ExchangeSaleLine
from app.modules.ginning_bunt.repository import GinningBuntRepository
from app.modules.ginning_costing.models import GinningProductionCost
from app.modules.ginning_costing.repository import GinningProductionCostRepository
from app.modules.ginning_costing.schemas import (
    CostAllocationLineResponse,
    CostAllocationRequest,
    GinningProductionCostCreate,
    GinningProductionCostResponse,
    ProductionCostSummaryResponse,
    ProductProfitabilityResponse,
)
from app.modules.ginning_production.repository import GinningProductionOrderRepository
from app.shared.enums import CostAllocationMethod, GinningProductionStatus, GinningProductType


class GinningCostingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cost_repo = GinningProductionCostRepository(session)
        self.order_repo = GinningProductionOrderRepository(session)
        self.bunt_repo = GinningBuntRepository(session)
        self.receiving_repo = CottonReceivingRepository(session)

    async def add_cost(
        self, company_id: uuid.UUID, order_id: uuid.UUID, data: GinningProductionCostCreate, actor_id: uuid.UUID,
    ) -> GinningProductionCost:
        order = await self.order_repo.get_scoped_with_lines(order_id, company_id)
        if order is None:
            raise NotFoundError("GinningProductionOrder", order_id)
        return await self.cost_repo.create(
            company_id=company_id,
            production_order_id=order_id,
            cost_type=data.cost_type,
            amount=data.amount,
            currency=data.currency,
            notes=data.notes,
            created_by=actor_id,
        )

    async def _bunt_avg_price(self, bunt_id: uuid.UUID) -> Decimal:
        receivings = await self.receiving_repo.get_posted_for_bunt(bunt_id)
        total_kg = sum((r.net_weight_kg for r in receivings), Decimal("0"))
        if total_kg == 0:
            return Decimal("0")
        total_value = sum((r.net_weight_kg * (r.unit_price or Decimal("0")) for r in receivings), Decimal("0"))
        return total_value / total_kg

    async def compute_raw_material_cost(self, order) -> Decimal:
        total = Decimal("0")
        for input_line in order.inputs:
            avg_price = await self._bunt_avg_price(input_line.bunt_id)
            total += input_line.quantity_kg * avg_price
        return total

    async def get_cost_summary(
        self, company_id: uuid.UUID, order_id: uuid.UUID, request: CostAllocationRequest,
    ) -> ProductionCostSummaryResponse:
        order = await self.order_repo.get_scoped_with_lines(order_id, company_id)
        if order is None:
            raise NotFoundError("GinningProductionOrder", order_id)

        raw_material_cost = await self.compute_raw_material_cost(order)
        other_costs = await self.cost_repo.list_for_order(order_id)
        other_costs_total = sum((c.amount for c in other_costs), Decimal("0"))
        total_cost = raw_material_cost + other_costs_total

        allocations = await self._allocate(order, total_cost, request)

        return ProductionCostSummaryResponse(
            production_order_id=order.id,
            production_number=order.production_number,
            raw_material_cost=raw_material_cost,
            other_costs=[
                GinningProductionCostResponse(
                    id=c.id, production_order_id=c.production_order_id, cost_type=c.cost_type,
                    amount=c.amount, currency=c.currency, notes=c.notes, created_at=c.created_at,
                )
                for c in other_costs
            ],
            other_costs_total=other_costs_total,
            total_cost=total_cost,
            allocation_method=request.method,
            allocations=allocations,
        )

    async def _reference_sales_price(self, company_id: uuid.UUID, product_type: GinningProductType) -> Decimal:
        """Weighted-average actual sale price for a product, from all (non-fully-cancelled) exchange sale lines."""
        result = await self.session.execute(
            select(ExchangeSaleLine)
            .join(ExchangeSale, ExchangeSaleLine.sale_id == ExchangeSale.id)
            .where(ExchangeSale.company_id == company_id, ExchangeSaleLine.product_type == product_type)
        )
        lines = list(result.scalars().all())
        total_kg = sum(((l.quantity_kg - l.cancelled_kg) for l in lines), Decimal("0"))
        if total_kg <= 0:
            return Decimal("0")
        total_value = sum(((l.quantity_kg - l.cancelled_kg) * l.unit_price for l in lines), Decimal("0"))
        return total_value / total_kg

    async def _allocate(
        self, order, total_cost: Decimal, request: CostAllocationRequest,
    ) -> list[CostAllocationLineResponse]:
        outputs = order.outputs
        total_output_kg = sum((o.quantity_kg for o in outputs), Decimal("0"))
        if total_output_kg == 0 or not outputs:
            return []

        if request.method == CostAllocationMethod.QUANTITY:
            weights = {o.id: o.quantity_kg for o in outputs}
            total_weight = total_output_kg

        elif request.method == CostAllocationMethod.SALES_VALUE:
            weights = {}
            for o in outputs:
                price = await self._reference_sales_price(order.company_id, o.product_type)
                weights[o.id] = o.quantity_kg * price
            total_weight = sum(weights.values(), Decimal("0"))
            if total_weight <= 0:
                raise BusinessRuleViolationError(
                    "No sales-value reference available for any output product — "
                    "record at least one exchange sale first, or use QUANTITY / MANUAL_PERCENTAGE allocation"
                )

        elif request.method == CostAllocationMethod.MANUAL_PERCENTAGE:
            if not request.manual_percentages:
                raise BusinessRuleViolationError("manual_percentages is required for MANUAL_PERCENTAGE allocation")
            provided_ids = set(request.manual_percentages.keys())
            output_ids = {o.id for o in outputs}
            if provided_ids != output_ids:
                raise BusinessRuleViolationError("manual_percentages must specify exactly one entry per output line")
            pct_sum = sum(request.manual_percentages.values(), Decimal("0"))
            if abs(pct_sum - Decimal("100")) > Decimal("0.01"):
                raise BusinessRuleViolationError(f"manual_percentages must sum to 100, got {pct_sum}")
            weights = {oid: pct for oid, pct in request.manual_percentages.items()}
            total_weight = Decimal("100")
        else:
            raise BusinessRuleViolationError(f"Unsupported allocation method: {request.method}")

        result = []
        for o in outputs:
            share = (weights[o.id] / total_weight) if total_weight > 0 else Decimal("0")
            allocated = total_cost * share
            result.append(CostAllocationLineResponse(
                output_id=o.id,
                product_type=o.product_type,
                quantity_kg=o.quantity_kg,
                allocated_cost=allocated,
                cost_per_kg=(allocated / o.quantity_kg) if o.quantity_kg > 0 else Decimal("0"),
            ))
        return result

    async def get_product_profitability(
        self, company_id: uuid.UUID, date_from: date | None = None, date_to: date | None = None,
    ) -> list[ProductProfitabilityResponse]:
        """
        Company-wide, product-level rollup: total sales value minus QUANTITY-allocated
        production cost (aggregated across all COMPLETED orders in range) minus
        pro-rated sales expenses (commission/broker/transport/other costs, allocated
        by each sale's share of total sale value).
        Uses QUANTITY allocation for this aggregate view since it requires no
        external price reference and is always computable.
        """
        order_conditions = [
            self.order_repo.model.company_id == company_id,
            self.order_repo.model.status == GinningProductionStatus.COMPLETED,
        ]
        if date_from is not None:
            order_conditions.append(self.order_repo.model.production_date >= date_from)
        if date_to is not None:
            order_conditions.append(self.order_repo.model.production_date <= date_to)

        result = await self.session.execute(select(self.order_repo.model).where(*order_conditions))
        orders = list(result.scalars().all())

        cost_by_product: dict[GinningProductType, Decimal] = {}
        for order in orders:
            order = await self.order_repo.get_scoped_with_lines(order.id, company_id)
            raw_cost = await self.compute_raw_material_cost(order)
            other_costs = await self.cost_repo.list_for_order(order.id)
            total_cost = raw_cost + sum((c.amount for c in other_costs), Decimal("0"))
            allocations = await self._allocate(
                order, total_cost, CostAllocationRequest(method=CostAllocationMethod.QUANTITY)
            )
            for a in allocations:
                cost_by_product[a.product_type] = cost_by_product.get(a.product_type, Decimal("0")) + a.allocated_cost

        sale_conditions = [ExchangeSale.company_id == company_id]
        if date_from is not None:
            sale_conditions.append(ExchangeSale.sale_date >= date_from)
        if date_to is not None:
            sale_conditions.append(ExchangeSale.sale_date <= date_to)
        result = await self.session.execute(
            select(ExchangeSaleLine, ExchangeSale)
            .join(ExchangeSale, ExchangeSaleLine.sale_id == ExchangeSale.id)
            .where(*sale_conditions)
        )
        rows = result.all()

        total_sale_value_all = sum(
            ((l.quantity_kg - l.cancelled_kg) * l.unit_price for l, _ in rows), Decimal("0")
        )
        value_by_product: dict[GinningProductType, Decimal] = {}
        qty_by_product: dict[GinningProductType, Decimal] = {}
        expenses_by_product: dict[GinningProductType, Decimal] = {}
        for line, sale in rows:
            net_kg = line.quantity_kg - line.cancelled_kg
            line_value = net_kg * line.unit_price
            value_by_product[line.product_type] = value_by_product.get(line.product_type, Decimal("0")) + line_value
            qty_by_product[line.product_type] = qty_by_product.get(line.product_type, Decimal("0")) + net_kg

            sale_expenses = sum(
                filter(None, [sale.commission_amount, sale.transport_cost, sale.other_costs]), Decimal("0")
            )
            line_share = (line_value / total_sale_value_all) if total_sale_value_all > 0 else Decimal("0")
            expenses_by_product[line.product_type] = (
                expenses_by_product.get(line.product_type, Decimal("0")) + sale_expenses * line_share
            )

        all_products = set(cost_by_product) | set(value_by_product)
        return [
            ProductProfitabilityResponse(
                product_type=p,
                total_sales_value=value_by_product.get(p, Decimal("0")),
                total_allocated_cost=cost_by_product.get(p, Decimal("0")),
                total_allocated_sales_expenses=expenses_by_product.get(p, Decimal("0")),
                profit=(
                    value_by_product.get(p, Decimal("0"))
                    - cost_by_product.get(p, Decimal("0"))
                    - expenses_by_product.get(p, Decimal("0"))
                ),
                total_quantity_sold_kg=qty_by_product.get(p, Decimal("0")),
            )
            for p in sorted(all_products, key=lambda x: x.value)
        ]
