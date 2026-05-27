import uuid
from dataclasses import dataclass


@dataclass
class AuditContext:
    """Carries the actor information needed for audit logging."""
    actor_id: uuid.UUID
    actor_username: str
    actor_full_name: str
    company_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
