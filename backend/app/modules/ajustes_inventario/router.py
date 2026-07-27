from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import UsuarioActual, get_current_user, require_admin
from app.modules.ajustes_inventario.schemas import AjusteInventarioCreate, AjusteInventarioOut
from app.modules.ajustes_inventario.service import crear_ajuste, listar_ajustes

# Ver es de cualquier usuario logueado; crear un ajuste (corrección manual de
# inventario) es exclusivo de administrador -- ver ../../../base-datos/README.md.
router = APIRouter(
    prefix="/ajustes-inventario", tags=["ajustes-inventario"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=PaginaOut[AjusteInventarioOut])
async def get_ajustes(
    material_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_ajustes(db, paginacion, material_id=material_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post(
    "", response_model=AjusteInventarioOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def post_ajuste(
    data: AjusteInventarioCreate,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    return await crear_ajuste(data, db, usuario.id)
