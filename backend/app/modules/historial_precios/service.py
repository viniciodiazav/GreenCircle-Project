from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.historial_precios.models import HistorialPrecio


async def listar_historial_precios(
    db: AsyncSession, paginacion: Paginacion, material_id: int | None = None
) -> tuple[list[HistorialPrecio], int]:
    stmt = select(HistorialPrecio).order_by(HistorialPrecio.fecha_cambio.desc())
    if material_id is not None:
        stmt = stmt.where(HistorialPrecio.material_id == material_id)
    return await ejecutar_paginado(stmt, db, paginacion)
