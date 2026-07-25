from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.historial_pacas.models import HistorialPaca

# Cruce deliberado (mismo patrón que detalle_salida -> pacas): filtrar el
# historial por material_id requiere el modelo Paca, que vive en su propio
# módulo, para hacer el join.
from app.modules.pacas.models import Paca


async def listar_historial_pacas(
    db: AsyncSession, paca_id: int | None = None, material_id: int | None = None
) -> list[HistorialPaca]:
    stmt = select(HistorialPaca).order_by(HistorialPaca.fecha.desc())
    if paca_id is not None:
        stmt = stmt.where(HistorialPaca.paca_id == paca_id)
    if material_id is not None:
        stmt = stmt.join(Paca, Paca.id == HistorialPaca.paca_id).where(Paca.material_id == material_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
