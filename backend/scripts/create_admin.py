import asyncio
from app.core.security import hash_password
# Ensure related model classes are imported so SQLAlchemy can resolve relationships
import app.modules.user.models  # noqa: F401
import app.modules.company.models  # noqa: F401
import app.modules.warehouse.models  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncEngine
from app.core.database import engine
from sqlalchemy import text


async def create_admin():
    hashed = hash_password('Admin1234!')
    # Insert directly via SQL to avoid ORM mapper import-time issues
    async with engine.begin() as conn:  # type: ignore[attr-defined]
        await conn.execute(
            text(
                """
                INSERT INTO users (id, username, full_name, hashed_password, is_active, is_superadmin, preferred_language)
                VALUES (gen_random_uuid(), :username, :full_name, :hashed_password, true, true, :preferred_language)
                ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password, preferred_language = EXCLUDED.preferred_language
                """
            ),
            {
                "username": "admin",
                "full_name": "System Administrator",
                "hashed_password": hashed,
                "preferred_language": "uz",
            },
        )
    print("Admin user created or updated: admin / Admin1234!")

if __name__ == '__main__':
    asyncio.run(create_admin())
