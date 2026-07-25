from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.historial_precios.models import HistorialPrecio


async def listar_historial_precios(
    db: AsyncSession, material_id: int | None = None
) -> list[HistorialPrecio]:
    stmt = select(HistorialPrecio).order_by(HistorialPrecio.fecha_cambio.desc())
    if material_id is not None:
        stmt = stmt.where(HistorialPrecio.material_id == material_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
