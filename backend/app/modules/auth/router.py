from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.auth.service import autenticar_admin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await autenticar_admin(data.usuario, data.password, db)
    return TokenResponse(access_token=token)
