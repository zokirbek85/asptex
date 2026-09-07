"""
T5a — concurrency regression tests:
  1. Partial unique index enforces at most one OPEN tolling lot per company,
     even when two requests race past the application-level has_open_lot()
     check at the same time.
"""
import asyncio
import uuid

import pytest

from app.modules.company.models import Company
from app.modules.tolling.schemas import TollingLotCreate
from app.modules.tolling.service import TollingService
from app.shared.base_service import AuditContext
from tests.conftest import TestSessionLocal


def _ctx() -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester")


@pytest.mark.asyncio
async def test_parallel_create_lot_only_one_succeeds():
    # Use a dedicated, committed company so two independent connections can
    # both see it (the shared `session`/`test_company` fixtures never commit).
    async with TestSessionLocal() as setup_session:
        company = Company(name="Concurrency Co", short_name="CC", tax_id="CONC-001")
        setup_session.add(company)
        await setup_session.commit()
        company_id = company.id

    async def attempt():
        async with TestSessionLocal() as s:
            svc = TollingService(s)
            async with s.begin():
                return await svc.create_lot(company_id, TollingLotCreate(notes=None), _ctx())

    results = await asyncio.gather(attempt(), attempt(), return_exceptions=True)
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"expected exactly 1 success, got: {results}"
    assert len(failures) == 1
