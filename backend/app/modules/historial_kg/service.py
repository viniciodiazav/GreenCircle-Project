from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.historial_kg.models import HistorialKg


async def listar_historial_kg(
    db: AsyncSession, paginacion: Paginacion, material_id: int | None = None
) -> tuple[list[HistorialKg], int]:
    stmt = select(HistorialKg).order_by(HistorialKg.fecha_cambio.desc())
    if material_id is not None:
        stmt = stmt.where(HistorialKg.material_id == material_id)
    return await ejecutar_paginado(stmt, db, paginacion)
