from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import UsuarioActual, require_admin
from app.modules.auth.schemas import (
    LoginRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioOut,
    UsuarioPatch,
)
from app.modules.auth.service import (
    actualizar_usuario,
    autenticar_usuario,
    crear_usuario,
    get_usuario_or_404,
    listar_usuarios,
)

# /auth: login público (único endpoint sin auth de todo el backend).
router = APIRouter(prefix="/auth", tags=["auth"])

# /usuarios: exclusivo de administrador (ver ../../../base-datos/README.md
# para la tabla completa de permisos por rol) -- un operador ni siquiera ve
# quién más tiene cuenta.
usuarios_router = APIRouter(
    prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(require_admin)]
)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await autenticar_usuario(data.usuario, data.password, db)
    return TokenResponse(access_token=token)


@usuarios_router.get("", response_model=PaginaOut[UsuarioOut])
async def get_usuarios(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    items, total = await listar_usuarios(db, paginacion)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@usuarios_router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def post_usuario(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    actor: UsuarioActual = Depends(require_admin),
):
    return await crear_usuario(data, db, actor)


@usuarios_router.get("/{usuario_id}", response_model=UsuarioOut)
async def get_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
    return await get_usuario_or_404(usuario_id, db)


@usuarios_router.patch("/{usuario_id}", response_model=UsuarioOut)
async def patch_usuario(
    usuario_id: int,
    data: UsuarioPatch,
    db: AsyncSession = Depends(get_db),
    actor: UsuarioActual = Depends(require_admin),
):
    return await actualizar_usuario(usuario_id, data, db, actor)
