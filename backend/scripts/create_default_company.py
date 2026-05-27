import asyncio
from sqlalchemy import text
from app.core.database import engine


async def create_default_company():
    async with engine.begin() as conn:
        # Get admin id
        res = await conn.execute(text("SELECT id FROM users WHERE username = :username"), {"username": "admin"})
        row = res.fetchone()
        if not row:
            print('Admin user not found')
            return
        admin_id = row[0]

        # Create company
        res = await conn.execute(
            text(
                """
                INSERT INTO companies (id, name, short_name, is_active)
                VALUES (gen_random_uuid(), :name, :short_name, true)
                RETURNING id
                """
            ),
            {"name": "Default Company", "short_name": "Default"},
        )
        company_row = res.fetchone()
        company_id = company_row[0]

        # Assign role
        await conn.execute(
            text(
                """
                INSERT INTO user_company_roles (id, user_id, company_id, role, is_active, created_by)
                VALUES (gen_random_uuid(), :user_id, :company_id, :role, true, :created_by)
                ON CONFLICT (user_id, company_id) DO NOTHING
                """
            ),
            {"user_id": admin_id, "company_id": company_id, "role": "ADMIN", "created_by": admin_id},
        )
    print('Default company created and admin assigned')


if __name__ == '__main__':
    asyncio.run(create_default_company())
