import uuid
from datetime import datetime
from typing import Any

from app.shared.schemas import AppBaseModel


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
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    reason: str | None
    ip_address: str | None
    created_at: datetime
