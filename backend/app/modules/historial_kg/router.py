from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.modules.historial_kg.schemas import HistorialKgOut
from app.modules.historial_kg.service import listar_historial_kg

router = APIRouter(prefix="/historial-kg", tags=["historial-kg"])


@router.get("", response_model=PaginaOut[HistorialKgOut])
async def get_historial_kg(
    material_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_historial_kg(db, paginacion, material_id=material_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)
