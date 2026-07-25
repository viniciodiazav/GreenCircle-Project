from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.modules.auth.models import Admin


async def autenticar_admin(usuario: str, password: str, db: AsyncSession) -> str:
    result = await db.execute(select(Admin).where(Admin.usuario == usuario))
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    return create_access_token(subject=admin.usuario)
