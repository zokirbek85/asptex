"""
Export service — generates Excel (.xlsx) and PDF reports.
Excel: openpyxl. PDF: weasyprint with Jinja2 HTML templates.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.daily_report.models import DailyReport
from app.modules.shipment.models import Shipment, ShipmentLine
from app.modules.stock.models import StockTransaction
from app.modules.warehouse.models import Warehouse
from app.shared.enums import WarehouseType

HEADER_FILL_HEX = "1a1a2e"
ALT_ROW_HEX = "f4f4f8"

# ── openpyxl helpers ──────────────────────────────────────────────────────────

def _make_workbook(company_name: str, report_title: str):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill, numbers
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = report_title[:31]

    # Title row
    ws.merge_cells("A1:J1")
    title_cell = ws["A1"]
    title_cell.value = f"{company_name} — {report_title}"
    title_cell.font = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal="center")

    ws.append([])  # blank row
    return wb, ws


def _write_header(ws, headers: list[str]):
    from openpyxl.styles import Alignment, Font, PatternFill

    row = ws.append
    row(headers)
    header_row = ws.max_row
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = PatternFill("solid", fgColor=HEADER_FILL_HEX)
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")


def _write_data_rows(ws, rows: list[list], number_cols: set[int] | None = None):
    from openpyxl.styles import Alignment, PatternFill

    start = ws.max_row + 1
    for i, row_data in enumerate(rows):
        ws.append(row_data)
        row_idx = start + i
        fill_color = ALT_ROW_HEX if i % 2 == 1 else "FFFFFF"
        for col_idx, _ in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.fill = PatternFill("solid", fgColor=fill_color)
            if number_cols and col_idx in number_cols:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.000"


def _autofit(ws):
    from openpyxl.utils import get_column_letter

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)


def _add_footer(ws, generated_at: datetime):
    ws.append([])
    ws.append([f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}"])


def _to_bytes(wb) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── PDF helper ────────────────────────────────────────────────────────────────

def _render_pdf(html: str) -> bytes:
    import weasyprint
    return weasyprint.HTML(string=html).write_pdf()


def _pdf_html(
    company_name: str,
    title: str,
    headers: list[str],
    rows: list[list],
    generated_at: datetime,
) -> str:
    header_cells = "".join(f"<th>{h}</th>" for h in headers)
    data_rows_html = ""
    for i, row in enumerate(rows):
        cls = "alt" if i % 2 == 1 else ""
        cells = "".join(f"<td>{c}</td>" for c in row)
        data_rows_html += f'<tr class="{cls}">{cells}</tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 10px; margin: 20px; }}
  h1 {{ font-size: 14px; text-align: center; }}
  h2 {{ font-size: 11px; text-align: center; color: #555; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #{HEADER_FILL_HEX}; color: white; padding: 4px 6px; text-align: center; }}
  td {{ padding: 3px 5px; border-bottom: 1px solid #ddd; }}
  tr.alt {{ background: #{ALT_ROW_HEX}; }}
  .footer {{ margin-top: 20px; font-size: 8px; color: #888; text-align: right; }}
  @page {{ size: A4 landscape; margin: 1cm; }}
  @page {{ @bottom-right {{ content: "Page " counter(page) " of " counter(pages); }} }}
</style></head><body>
<h1>{company_name}</h1><h2>{title}</h2>
<table><thead><tr>{header_cells}</tr></thead><tbody>{data_rows_html}</tbody></table>
<div class="footer">Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}</div>
</body></html>"""


# ── Export Service ────────────────────────────────────────────────────────────

class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _company_name(self, company_id: uuid.UUID) -> str:
        from app.modules.company.models import Company
        result = await self.session.execute(
            select(Company.name).where(Company.id == company_id)
        )
        return result.scalar_one_or_none() or "Company"

    async def export_stock_report(
        self,
        company_id: uuid.UUID,
        fmt: str,
        warehouse_type: WarehouseType | None = None,
        as_of_date: date | None = None,
    ) -> bytes:
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)
        title = "Stock Report"
        if as_of_date:
            title += f" as of {as_of_date}"

        wh_cond = [
            Warehouse.company_id == company_id,
            Warehouse.is_active == True,
        ]
        if warehouse_type is not None:
            wh_cond.append(Warehouse.warehouse_type == warehouse_type)

        wh_result = await self.session.execute(
            select(Warehouse.id, Warehouse.name, Warehouse.warehouse_type).where(*wh_cond)
        )
        wh_map = {r.id: (r.name, r.warehouse_type) for r in wh_result.all()}

        if not wh_map:
            rows = []
        else:
            tx_cond = [
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id.in_(list(wh_map.keys())),
            ]
            if as_of_date:
                tx_cond.append(StockTransaction.transaction_date <= as_of_date)

            result = await self.session.execute(
                select(
                    StockTransaction.warehouse_id,
                    StockTransaction.lot_number,
                    StockTransaction.count_value,
                    StockTransaction.owner_name,
                    StockTransaction.waste_type,
                    StockTransaction.pkg_item_type,
                    func.sum(StockTransaction.quantity_kg * StockTransaction.direction).label("total_kg"),
                    func.sum(StockTransaction.quantity_bags * StockTransaction.direction).label("total_bags"),
                )
                .where(*tx_cond)
                .group_by(
                    StockTransaction.warehouse_id,
                    StockTransaction.lot_number,
                    StockTransaction.count_value,
                    StockTransaction.owner_name,
                    StockTransaction.waste_type,
                    StockTransaction.pkg_item_type,
                )
                .having(func.sum(StockTransaction.quantity_kg * StockTransaction.direction) > 0)
                .order_by(StockTransaction.lot_number, StockTransaction.count_value)
            )

            rows = []
            for r in result.all():
                wh_name = wh_map.get(r.warehouse_id, ("?", ""))[0]
                identifier = r.lot_number or (r.waste_type.value if r.waste_type else "") or (r.pkg_item_type.value if r.pkg_item_type else "")
                rows.append([
                    wh_name,
                    identifier,
                    r.count_value or "",
                    r.owner_name or "Own",
                    float(r.total_kg) if r.total_kg else 0,
                    int(r.total_bags) if r.total_bags else 0,
                ])

        headers = ["Warehouse", "Lot / Type", "Count", "Owner", "Qty (kg)", "Bags"]

        if fmt == "pdf":
            return _render_pdf(_pdf_html(co_name, title, headers, rows, generated))

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows, number_cols={5, 6})
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)

    async def export_shipments(
        self,
        company_id: uuid.UUID,
        fmt: str,
        date_from: date | None = None,
        date_to: date | None = None,
        buyer_id: uuid.UUID | None = None,
    ) -> bytes:
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)
        title = "Shipment Register"

        conditions = [Shipment.company_id == company_id]
        if date_from:
            conditions.append(Shipment.shipment_date >= date_from)
        if date_to:
            conditions.append(Shipment.shipment_date <= date_to)
        if buyer_id:
            conditions.append(Shipment.buyer_id == buyer_id)

        result = await self.session.execute(
            select(Shipment).where(*conditions).order_by(Shipment.shipment_date.desc())
        )
        shipments = list(result.scalars().all())

        rows = []
        for s in shipments:
            total_result = await self.session.execute(
                select(func.sum(ShipmentLine.quantity_kg)).where(ShipmentLine.shipment_id == s.id)
            )
            total_kg = float(total_result.scalar_one() or 0)
            rows.append([
                s.shipment_number,
                str(s.shipment_date),
                str(s.buyer_id),
                s.status.value,
                total_kg,
            ])

        headers = ["Shipment #", "Date", "Buyer ID", "Status", "Total (kg)"]

        if fmt == "pdf":
            return _render_pdf(_pdf_html(co_name, title, headers, rows, generated))

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows, number_cols={5})
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)

    async def export_daily_report(
        self,
        company_id: uuid.UUID,
        report_id: uuid.UUID,
        fmt: str,
    ) -> bytes:
        from sqlalchemy.orm import selectinload
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)

        report_result = await self.session.execute(
            select(DailyReport)
            .options(selectinload(DailyReport.lines))
            .where(DailyReport.id == report_id)
        )
        report = report_result.scalar_one_or_none()
        if report is None:
            return b""

        title = f"Daily Report {report.report_date} ({report.status.value})"
        headers = ["#", "Category", "Lot", "Count", "Owner/Waste/Pkg", "Qty (kg)", "Bags/Units"]
        rows = []
        for line in (report.lines or []):
            rows.append([
                line.line_number,
                line.line_category.value,
                line.lot_id or "",
                line.count_id or "",
                str(line.owner_id or line.waste_type or line.pkg_item_type or ""),
                float(line.quantity_kg),
                line.quantity_bags or line.quantity_units or "",
            ])

        if fmt == "pdf":
            return _render_pdf(_pdf_html(co_name, title, headers, rows, generated))

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows, number_cols={6})
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)

    async def export_lot_card(
        self,
        company_id: uuid.UUID,
        lot_id: uuid.UUID,
        fmt: str,
    ) -> bytes:
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(StockTransaction)
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.lot_id == lot_id,
            )
            .order_by(StockTransaction.transaction_date, StockTransaction.posted_at)
        )
        txs = list(result.scalars().all())
        lot_number = txs[0].lot_number if txs else str(lot_id)
        title = f"Lot Card: {lot_number}"
        headers = ["Date", "Type", "Direction", "Qty (kg)", "Bags", "Count", "Owner", "Ref"]
        rows = []
        for tx in txs:
            rows.append([
                str(tx.transaction_date),
                tx.transaction_type.value,
                "+" if tx.direction == 1 else "-",
                float(tx.quantity_kg),
                tx.quantity_bags or "",
                tx.count_value or "",
                tx.owner_name or "",
                tx.reference_type or "",
            ])

        if fmt == "pdf":
            return _render_pdf(_pdf_html(co_name, title, headers, rows, generated))

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows, number_cols={4})
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)

    async def export_waste_report(
        self,
        company_id: uuid.UUID,
        fmt: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> bytes:
        from app.modules.waste.schemas import WASTE_TYPE_LABELS
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)
        title = "Waste Report"

        conditions = [
            StockTransaction.company_id == company_id,
            StockTransaction.waste_type.is_not(None),
        ]
        if date_from:
            conditions.append(StockTransaction.transaction_date >= date_from)
        if date_to:
            conditions.append(StockTransaction.transaction_date <= date_to)

        result = await self.session.execute(
            select(
                StockTransaction.waste_type,
                StockTransaction.transaction_type,
                func.sum(StockTransaction.quantity_kg).label("total_kg"),
            )
            .where(*conditions)
            .group_by(StockTransaction.waste_type, StockTransaction.transaction_type)
            .order_by(StockTransaction.waste_type)
        )
        rows = [
            [
                WASTE_TYPE_LABELS.get(r.waste_type, r.waste_type.value),
                r.transaction_type.value,
                float(r.total_kg),
            ]
            for r in result.all()
        ]
        headers = ["Waste Type", "Transaction Type", "Qty (kg)"]

        if fmt == "pdf":
            return _render_pdf(_pdf_html(co_name, title, headers, rows, generated))

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows, number_cols={3})
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)

    async def export_audit_log(
        self,
        company_id: uuid.UUID,
        fmt: str,
        date_from: date | None = None,
        date_to: date | None = None,
        entity_type: str | None = None,
    ) -> bytes:
        co_name = await self._company_name(company_id)
        generated = datetime.now(timezone.utc)
        title = "Audit Log"

        conditions = [AuditLog.company_id == company_id]
        if date_from:
            conditions.append(func.date(AuditLog.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(AuditLog.created_at) <= date_to)
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)

        result = await self.session.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .limit(10000)
        )
        logs = list(result.scalars().all())
        headers = ["Timestamp", "Actor", "Action", "Entity Type", "Entity", "Reason"]
        rows = [
            [
                str(log.created_at),
                log.actor_username,
                log.action,
                log.entity_type,
                log.entity_display or str(log.entity_id or ""),
                log.reason or "",
            ]
            for log in logs
        ]

        wb, ws = _make_workbook(co_name, title)
        _write_header(ws, headers)
        _write_data_rows(ws, rows)
        _add_footer(ws, generated)
        _autofit(ws)
        return _to_bytes(wb)
