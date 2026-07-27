from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import UsuarioActual, get_current_user
from app.modules.detalle_entrada.schemas import (
    DetalleEntradaCreate,
    DetalleEntradaOut,
    DetalleEntradaPatch,
)
from app.modules.detalle_entrada.service import (
    actualizar_detalle_entrada,
    agregar_detalle_entrada,
    cancelar_detalle_entrada,
    get_detalle_entrada_or_404,
    listar_detalle_entrada,
)

router = APIRouter(
    prefix="/detalle-entrada", tags=["detalle-entrada"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=PaginaOut[DetalleEntradaOut])
async def get_detalles_entrada(
    movimiento_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_detalle_entrada(db, paginacion, movimiento_id=movimiento_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post("", response_model=DetalleEntradaOut, status_code=status.HTTP_201_CREATED)
async def post_detalle_entrada(
    data: DetalleEntradaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    return await agregar_detalle_entrada(data, db, usuario.id)


@router.get("/{detalle_id}", response_model=DetalleEntradaOut)
async def get_detalle_entrada(detalle_id: int, db: AsyncSession = Depends(get_db)):
    return await get_detalle_entrada_or_404(detalle_id, db)


@router.patch("/{detalle_id}", response_model=DetalleEntradaOut)
async def patch_detalle_entrada(
    detalle_id: int, data: DetalleEntradaPatch, db: AsyncSession = Depends(get_db)
):
    return await actualizar_detalle_entrada(detalle_id, data, db)


@router.delete("/{detalle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detalle_entrada(
    detalle_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    await cancelar_detalle_entrada(detalle_id, db, usuario.id)
