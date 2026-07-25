from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.historial_kg.schemas import HistorialKgOut
from app.modules.historial_kg.service import listar_historial_kg

router = APIRouter(prefix="/historial-kg", tags=["historial-kg"])


@router.get("", response_model=list[HistorialKgOut])
async def get_historial_kg(
    material_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_historial_kg(db, material_id=material_id)
