from datetime import date
import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.dependencies import AdminDep, SessionDep
from app.modules.audit.models import AuditLog
from app.shared.schemas import AppBaseModel, PaginatedResponse

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(AppBaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    actor_id: uuid.UUID
    actor_username: str
    actor_full_name: str
    entity_type: str
    entity_id: uuid.UUID | None
    entity_display: str | None
    action: str
    reason: str | None
    ip_address: str | None
    created_at: str


@router.get("/", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_log(
    session: SessionDep,
    current_user: AdminDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    entity_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    actor: str | None = Query(None),
) -> PaginatedResponse[AuditLogResponse]:
    async with session.begin():
        conditions = [AuditLog.company_id == current_user.company_id]
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if date_from:
            conditions.append(func.date(AuditLog.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(AuditLog.created_at) <= date_to)
        if actor:
            conditions.append(AuditLog.actor_username.ilike(f"%{actor}%"))

        total_result = await session.execute(
            select(func.count(AuditLog.id)).where(*conditions)
        )
        total = total_result.scalar_one()

        result = await session.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = list(result.scalars().all())

    items = [
        AuditLogResponse(
            id=log.id,
            company_id=log.company_id,
            actor_id=log.actor_id,
            actor_username=log.actor_username,
            actor_full_name=log.actor_full_name,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            entity_display=log.entity_display,
            action=log.action,
            reason=log.reason,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]
    return PaginatedResponse.build(items, total, page, page_size)
