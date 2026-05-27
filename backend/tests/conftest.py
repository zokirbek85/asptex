import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.modules.auth.models import User
from app.modules.company.models import Company
from app.modules.user.models import UserCompanyRole
from app.modules.warehouse.models import Warehouse
from app.shared.base_model import Base
from app.shared.enums import UserRole, WarehouseType

# Use a separate test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/asptex", "/asptex_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── Test data fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_company(session: AsyncSession) -> Company:
    company = Company(name="Test Company", short_name="TC", tax_id="TEST-001")
    session.add(company)
    await session.flush()
    return company


@pytest_asyncio.fixture
async def test_warehouse(session: AsyncSession, test_company: Company) -> Warehouse:
    wh = Warehouse(
        company_id=test_company.id,
        code="WH-FG-01",
        name="Finished Goods",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def test_admin_user(session: AsyncSession, test_company: Company) -> User:
    user = User(
        username="test_admin",
        full_name="Test Admin",
        hashed_password=hash_password("TestPass123!"),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    role = UserCompanyRole(
        user_id=user.id,
        company_id=test_company.id,
        role=UserRole.ADMIN,
    )
    session.add(role)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, test_admin_user: User) -> str:
    resp = await client.post("/api/v1/auth/login", json={
        "username": "test_admin",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]
