from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.historial_pacas.schemas import HistorialPacaOut
from app.modules.historial_pacas.service import listar_historial_pacas

router = APIRouter(prefix="/historial-pacas", tags=["historial-pacas"])


@router.get("", response_model=list[HistorialPacaOut])
async def get_historial_pacas(
    paca_id: int | None = Query(default=None),
    material_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await listar_historial_pacas(db, paca_id=paca_id, material_id=material_id)
