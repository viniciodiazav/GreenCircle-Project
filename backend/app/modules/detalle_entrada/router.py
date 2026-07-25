from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.detalle_entrada.schemas import DetalleEntradaCreate, DetalleEntradaOut
from app.modules.detalle_entrada.service import (
    agregar_detalle_entrada,
    get_detalle_entrada_or_404,
    listar_detalle_entrada,
)

router = APIRouter(prefix="/detalle-entrada", tags=["detalle-entrada"])


@router.get("", response_model=list[DetalleEntradaOut])
async def get_detalles_entrada(
    movimiento_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_detalle_entrada(db, movimiento_id=movimiento_id)


@router.post("", response_model=DetalleEntradaOut, status_code=status.HTTP_201_CREATED)
async def post_detalle_entrada(data: DetalleEntradaCreate, db: AsyncSession = Depends(get_db)):
    return await agregar_detalle_entrada(data, db)


@router.get("/{detalle_id}", response_model=DetalleEntradaOut)
async def get_detalle_entrada(detalle_id: int, db: AsyncSession = Depends(get_db)):
    return await get_detalle_entrada_or_404(detalle_id, db)
