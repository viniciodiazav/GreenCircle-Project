from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import get_current_user
from app.modules.historial_precios.schemas import HistorialPrecioOut
from app.modules.historial_precios.service import listar_historial_precios

router = APIRouter(
    prefix="/historial-precios", tags=["historial-precios"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=PaginaOut[HistorialPrecioOut])
async def get_historial_precios(
    material_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_historial_precios(db, paginacion, material_id=material_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)
