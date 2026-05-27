"""seed default company for admin

Revision ID: 20260528_seed_default_company
Revises: 93baddec29d8
Create Date: 2026-05-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260528_seed_default_company'
down_revision = '93baddec29d8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
    DO $$
    DECLARE admin_id uuid;
    company_id uuid;
    BEGIN
      SELECT id INTO admin_id FROM users WHERE username='admin';
      IF admin_id IS NULL THEN
        RETURN;
      END IF;
      SELECT id INTO company_id FROM companies WHERE name='Default Company';
      IF company_id IS NULL THEN
        INSERT INTO companies (id, name, short_name, is_active)
        VALUES (gen_random_uuid(), 'Default Company', 'Default', true)
        RETURNING id INTO company_id;
      END IF;
      IF NOT EXISTS (SELECT 1 FROM user_company_roles WHERE user_id=admin_id AND company_id=company_id) THEN
        INSERT INTO user_company_roles (id, user_id, company_id, role, is_active, created_by)
        VALUES (gen_random_uuid(), admin_id, company_id, 'ADMIN', true, admin_id);
      END IF;
    END$$;
    """))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
    DO $$
    DECLARE admin_id uuid;
    company_id uuid;
    BEGIN
      SELECT id INTO admin_id FROM users WHERE username='admin';
      IF admin_id IS NULL THEN
        RETURN;
      END IF;
      SELECT id INTO company_id FROM companies WHERE name='Default Company';
      IF company_id IS NULL THEN
        RETURN;
      END IF;
      DELETE FROM user_company_roles WHERE user_id=admin_id AND company_id=company_id;
      DELETE FROM companies WHERE id=company_id;
    END$$;
    """))
