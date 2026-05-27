import asyncio
from sqlalchemy import text
from app.core.database import engine


async def get_admin():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, username, full_name, email, is_active, is_superadmin, preferred_language, created_at FROM users WHERE username = :username"),
            {"username": "admin"},
        )
        row = result.fetchone()
        if not row:
            print('No admin user found')
            return
        # Print columns
        cols = result.keys()
        for k, v in zip(cols, row):
            print(f"{k}: {v}")


if __name__ == '__main__':
    asyncio.run(get_admin())
