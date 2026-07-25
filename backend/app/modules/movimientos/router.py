from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.movimientos.schemas import MovimientoCreate, MovimientoOut
from app.modules.movimientos.service import (
    cerrar_movimiento,
    crear_movimiento,
    get_movimiento_or_404,
    listar_movimientos,
)

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.get("", response_model=list[MovimientoOut])
async def get_movimientos(
    tipo: str | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_movimientos(db, tipo=tipo)


@router.post("", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def post_movimiento(data: MovimientoCreate, db: AsyncSession = Depends(get_db)):
    return await crear_movimiento(data, db)


@router.get("/{movimiento_id}", response_model=MovimientoOut)
async def get_movimiento(movimiento_id: int, db: AsyncSession = Depends(get_db)):
    return await get_movimiento_or_404(movimiento_id, db)


@router.patch("/{movimiento_id}/cerrar", response_model=MovimientoOut)
async def patch_cerrar_movimiento(movimiento_id: int, db: AsyncSession = Depends(get_db)):
    return await cerrar_movimiento(movimiento_id, db)
