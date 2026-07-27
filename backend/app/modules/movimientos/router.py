from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import UsuarioActual, get_current_user
from app.modules.movimientos.schemas import MovimientoCreate, MovimientoOut, MovimientoPatch
from app.modules.movimientos.service import (
    actualizar_movimiento,
    cancelar_movimiento,
    cerrar_movimiento,
    crear_movimiento,
    get_movimiento_or_404,
    listar_movimientos,
)

router = APIRouter(prefix="/movimientos", tags=["movimientos"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginaOut[MovimientoOut])
async def get_movimientos(
    tipo: str | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_movimientos(db, paginacion, tipo=tipo)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post("", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def post_movimiento(
    data: MovimientoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    return await crear_movimiento(data, db, usuario.id)


@router.get("/{movimiento_id}", response_model=MovimientoOut)
async def get_movimiento(movimiento_id: int, db: AsyncSession = Depends(get_db)):
    return await get_movimiento_or_404(movimiento_id, db)


@router.patch("/{movimiento_id}", response_model=MovimientoOut)
async def patch_movimiento(
    movimiento_id: int, data: MovimientoPatch, db: AsyncSession = Depends(get_db)
):
    return await actualizar_movimiento(movimiento_id, data, db)


@router.patch("/{movimiento_id}/cerrar", response_model=MovimientoOut)
async def patch_cerrar_movimiento(movimiento_id: int, db: AsyncSession = Depends(get_db)):
    return await cerrar_movimiento(movimiento_id, db)


@router.delete("/{movimiento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movimiento(movimiento_id: int, db: AsyncSession = Depends(get_db)):
    await cancelar_movimiento(movimiento_id, db)
