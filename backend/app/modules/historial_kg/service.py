from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.historial_kg.models import HistorialKg


async def listar_historial_kg(db: AsyncSession, material_id: int | None = None) -> list[HistorialKg]:
    stmt = select(HistorialKg).order_by(HistorialKg.fecha_cambio.desc())
    if material_id is not None:
        stmt = stmt.where(HistorialKg.material_id == material_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
