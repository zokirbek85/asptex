# ASPTEX — Local Development Guide

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| Docker Desktop | 4.x | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled) | — |
| Node.js | 20 LTS | https://nodejs.org/ (only needed to run frontend outside Docker) |
| Python | 3.11+ | https://python.org/ (only needed to run backend outside Docker) |

---

## Quick Start (Docker — recommended)

### 1. Clone & configure environment

```bash
cd asptex
cp .env.example .env
```

Open `.env` and set:

```env
POSTGRES_PASSWORD=any_local_password
SECRET_KEY=<run: openssl rand -hex 32>
```

> On Windows PowerShell if you don't have `openssl`:
> ```powershell
> [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }))
> ```

### 2. Start all services

```bash
docker compose up --build
```

This starts: **postgres:5432 → redis:6379 → backend:8000 → frontend:3000 → nginx:80**

The backend container automatically runs `alembic upgrade head` on startup.

### 3. Open in browser

| URL | What |
|-----|------|
| http://localhost | App (via Nginx reverse proxy) |
| http://localhost:3000 | Frontend direct |
| http://localhost:8000 | Backend API direct |
| http://localhost:8000/api/docs | Swagger UI (DEBUG=true only) |
| http://localhost:8000/api/redoc | ReDoc (DEBUG=true only) |

### 4. Create the first superadmin user

```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import get_session
from app.core.security import hash_password
from app.modules.auth.models import User
from sqlalchemy.ext.asyncio import AsyncSession

async def create_admin():
    from app.core.database import engine
    from app.shared.base_model import Base
    async with AsyncSession(engine) as session:
        async with session.begin():
            user = User(
                username='admin',
                full_name='System Administrator',
                hashed_password=hash_password('Admin1234!'),
                is_active=True,
                is_superadmin=True,
            )
            session.add(user)
    print('Admin user created: admin / Admin1234!')

asyncio.run(create_admin())
"
```

Then log in at http://localhost/login with `admin` / `Admin1234!`.

---

## Running without Docker (native)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables (PowerShell)
$env:DATABASE_URL = "postgresql+asyncpg://asptex:asptex_secret@localhost:5432/asptex"
$env:SECRET_KEY   = "dev_secret_key_change_in_prod"
$env:DEBUG        = "true"

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> Requires a running PostgreSQL instance on localhost:5432.
> Use `docker compose up postgres redis` to start only the databases.

### Frontend

```bash
cd frontend

npm install

# Create local env file
cp ../.env.example .env.local
# Edit NEXT_PUBLIC_API_URL:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

npm run dev
```

Frontend runs at http://localhost:3000.

---

## Database Migrations

### Apply all pending migrations

```bash
# In Docker:
docker compose exec backend alembic upgrade head

# Native:
cd backend && alembic upgrade head
```

### Create a new migration

```bash
# In Docker:
docker compose exec backend alembic revision --autogenerate -m "describe_change"

# Native:
cd backend && alembic revision --autogenerate -m "describe_change"
```

The generated file appears in `backend/migrations/versions/`. Always review it before applying.

### Rollback one step

```bash
docker compose exec backend alembic downgrade -1
```

---

## Useful Docker Commands

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart one service after code change (backend hot-reloads automatically)
docker compose restart backend

# Stop everything
docker compose down

# Stop and wipe database volume (full reset)
docker compose down -v

# Open a shell inside the backend container
docker compose exec backend bash

# Open psql
docker compose exec postgres psql -U asptex -d asptex
```

---

## Project Structure

```
asptex/
├── .env.example          # Environment template — copy to .env
├── docker-compose.yml    # Local dev: all 5 services
├── docker-compose.prod.yml
├── nginx/
│   └── nginx.conf
├── backend/
│   ├── app/
│   │   ├── core/         # config, security, dependencies, exceptions, middleware
│   │   ├── modules/      # one directory per domain module
│   │   │   ├── auth/
│   │   │   ├── company/
│   │   │   ├── user/
│   │   │   ├── warehouse/
│   │   │   ├── counterparty/
│   │   │   ├── contract/
│   │   │   ├── count_catalog/
│   │   │   ├── lot/
│   │   │   ├── stock/
│   │   │   ├── daily_report/
│   │   │   ├── shipment/
│   │   │   ├── adjustment/
│   │   │   └── audit/
│   │   └── shared/       # base models, repositories, schemas, enums, utils
│   ├── migrations/       # Alembic migration files
│   ├── tests/
│   └── pyproject.toml
└── frontend/
    ├── app/
    │   ├── (auth)/       # login, select-company pages
    │   └── (app)/        # authenticated app pages
    │       ├── dashboard/
    │       ├── admin/    # companies, users, warehouses
    │       └── master/   # counterparties, contracts, lots, counts
    ├── components/
    │   ├── layout/       # Sidebar, Topbar
    │   └── ui/           # Button, Input, Select, Modal, Badge, DataTable
    ├── lib/
    │   ├── api/          # API client modules per domain
    │   ├── stores/       # Zustand auth store
    │   └── types/        # TypeScript type definitions
    └── package.json
```

---

## API Documentation

Available at http://localhost:8000/api/docs (only when `DEBUG=true`).

### Authentication flow

1. `POST /api/v1/auth/login` → returns `access_token` (no company context) + `refresh_token` + list of companies
2. `POST /api/v1/auth/switch-company` → returns new `access_token` with `company_id` + `role` embedded
3. All subsequent requests: `Authorization: Bearer <access_token>`
4. Token refresh: `POST /api/v1/auth/refresh` with `refresh_token`

---

## Running Tests

```bash
# In Docker:
docker compose exec backend pytest

# Native:
cd backend && pytest

# With coverage:
pytest --cov=app --cov-report=term-missing
```

Tests use a separate database (`asptex_test`). The `conftest.py` creates it automatically if it doesn't exist and rolls back each test in a transaction.

---

## Code Quality

```bash
cd backend

# Lint
ruff check app/

# Format
ruff format app/

# Type check
mypy app/
```

```bash
cd frontend

# Type check
npm run type-check

# Lint
npm run lint
```

---

## Common Issues

**`alembic upgrade head` fails with "table already exists"**
The database has partial state. Connect via psql and drop the schema, or run:
```bash
docker compose down -v && docker compose up --build
```

**Backend container exits immediately**
Check logs: `docker compose logs backend`. Most likely cause is a missing env var or the database isn't ready yet. Ensure `postgres` passes its healthcheck before `backend` starts (already configured in `docker-compose.yml`).

**Frontend shows "Network Error" / 401 on every request**
Make sure `NEXT_PUBLIC_API_URL` points to the correct backend address. In Docker it should be `http://localhost/api/v1` (through Nginx). When running frontend natively against a native backend use `http://localhost:8000/api/v1`.

**Port conflict on 5432 / 80**
Stop any local PostgreSQL service or change the host port in `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"   # host:container
```
Then update `DATABASE_URL` accordingly.
