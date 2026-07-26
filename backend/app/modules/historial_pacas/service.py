from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.historial_pacas.models import HistorialPaca

# Cruce deliberado (mismo patrón que detalle_salida -> pacas): filtrar el
# historial por material_id requiere el modelo Paca, que vive en su propio
# módulo, para hacer el join.
from app.modules.pacas.models import Paca


async def listar_historial_pacas(
    db: AsyncSession,
    paginacion: Paginacion,
    paca_id: int | None = None,
    material_id: int | None = None,
) -> tuple[list[HistorialPaca], int]:
    stmt = select(HistorialPaca).order_by(HistorialPaca.fecha.desc())
    if paca_id is not None:
        stmt = stmt.where(HistorialPaca.paca_id == paca_id)
    if material_id is not None:
        stmt = stmt.join(Paca, Paca.id == HistorialPaca.paca_id).where(Paca.material_id == material_id)
    return await ejecutar_paginado(stmt, db, paginacion)
