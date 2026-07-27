from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import get_current_user
from app.modules.historial_pacas.schemas import HistorialPacaOut
from app.modules.historial_pacas.service import listar_historial_pacas

router = APIRouter(
    prefix="/historial-pacas", tags=["historial-pacas"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=PaginaOut[HistorialPacaOut])
async def get_historial_pacas(
    paca_id: int | None = Query(default=None),
    material_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_historial_pacas(db, paginacion, paca_id=paca_id, material_id=material_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)
