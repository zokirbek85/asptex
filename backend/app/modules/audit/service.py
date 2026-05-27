"""
AuditService — the single place that writes to audit_log.
Every write operation in the system MUST call AuditService.log().
The audit_log table is append-only; no updates or deletes are ever issued.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        *,
        ctx: AuditContext,
        entity_type: str,
        action: AuditAction,
        entity_id: uuid.UUID | None = None,
        entity_display: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            company_id=ctx.company_id,
            actor_id=ctx.actor_id,
            actor_username=ctx.actor_username,
            actor_full_name=ctx.actor_full_name,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_display=entity_display,
            action=action.value,
            before_data=before_data,
            after_data=after_data,
            reason=reason,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
        )
        self.session.add(entry)
        # Flush within the caller's transaction — do not commit here.
        await self.session.flush([entry])
        return entry
