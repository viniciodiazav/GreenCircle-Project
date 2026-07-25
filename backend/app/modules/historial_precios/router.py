from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.historial_precios.schemas import HistorialPrecioOut
from app.modules.historial_precios.service import listar_historial_precios

router = APIRouter(prefix="/historial-precios", tags=["historial-precios"])


@router.get("", response_model=list[HistorialPrecioOut])
async def get_historial_precios(
    material_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_historial_precios(db, material_id=material_id)
