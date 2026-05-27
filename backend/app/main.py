from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AppException,
    AuthenticationError,
    BusinessRuleViolationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.middleware import RequestContextMiddleware

# ── Router imports ────────────────────────────────────────────────────────────
from app.modules.auth.router import router as auth_router
from app.modules.company.router import router as company_router
from app.modules.counterparty.router import router as counterparty_router
from app.modules.contract.router import router as contract_router
from app.modules.count_catalog.router import router as count_router
from app.modules.lot.router import router as lot_router
from app.modules.user.router import router as user_router
from app.modules.warehouse.router import router as warehouse_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ASPTEX Textile Warehouse ERP — API",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.message, "code": exc.code},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(PermissionDeniedError)
async def permission_error_handler(request: Request, exc: PermissionDeniedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(AlreadyExistsError)
async def exists_handler(request: Request, exc: AlreadyExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "code": exc.code, "field": exc.field},
    )


@app.exception_handler(BusinessRuleViolationError)
async def business_rule_handler(request: Request, exc: BusinessRuleViolationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(AppException)
async def app_error_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(counterparty_router, prefix="/api/v1")
app.include_router(contract_router, prefix="/api/v1")
app.include_router(count_router, prefix="/api/v1")
app.include_router(lot_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}
