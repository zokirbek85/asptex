from fastapi import APIRouter, Request

from app.core.dependencies import AdminDep, SessionDep
from app.modules.data_reset.schemas import DATA_RESET_MODULES, DataResetRequest, DataResetResponse
from app.modules.data_reset.service import DataResetService

router = APIRouter(prefix="/admin/data-reset", tags=["admin"])


@router.get("/modules")
async def list_modules(current_user: AdminDep) -> list[str]:
    return DATA_RESET_MODULES


@router.post("/", response_model=DataResetResponse)
async def reset_data(
    body: DataResetRequest,
    request: Request,
    session: SessionDep,
    current_user: AdminDep,
) -> DataResetResponse:
    async with session.begin():
        svc = DataResetService(session)
        return await svc.reset(
            current_user.company_id,
            body.modules,
            body.confirm_company_name,
            current_user.to_audit_context(
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            ),
        )
