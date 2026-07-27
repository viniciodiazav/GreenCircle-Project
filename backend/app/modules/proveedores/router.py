from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import get_current_user
from app.modules.proveedores.schemas import ProveedorCreate, ProveedorOut, ProveedorPatch
from app.modules.proveedores.service import (
    actualizar_proveedor,
    crear_proveedor,
    get_proveedor_or_404,
    listar_proveedores,
)

router = APIRouter(prefix="/proveedores", tags=["proveedores"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginaOut[ProveedorOut])
async def get_proveedores(
    activo: bool | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    proveedores, total = await listar_proveedores(db, paginacion, activo=activo)
    return PaginaOut(items=proveedores, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
async def post_proveedor(data: ProveedorCreate, db: AsyncSession = Depends(get_db)):
    return await crear_proveedor(data, db)


@router.get("/{proveedor_id}", response_model=ProveedorOut)
async def get_proveedor(proveedor_id: int, db: AsyncSession = Depends(get_db)):
    return await get_proveedor_or_404(proveedor_id, db)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
async def patch_proveedor(
    proveedor_id: int, data: ProveedorPatch, db: AsyncSession = Depends(get_db)
):
    return await actualizar_proveedor(proveedor_id, data, db)
