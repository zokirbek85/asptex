import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.core.security import verify_password


async def check():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT username, hashed_password FROM users WHERE username = :username"),
            {"username": "admin"},
        )
        row = result.fetchone()
        if not row:
            print('No admin user found')
            return
        username, hashed = row
        ok = verify_password('Admin1234!', hashed)
        print(f'username={username} password_match={ok}')


if __name__ == '__main__':
    asyncio.run(check())
