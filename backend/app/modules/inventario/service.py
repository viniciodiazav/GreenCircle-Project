from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventario.models import Inventario, InventarioPacas


async def listar_inventario(db: AsyncSession) -> list[Inventario]:
    result = await db.execute(select(Inventario).order_by(Inventario.material_id))
    return list(result.scalars().all())


async def listar_inventario_pacas(db: AsyncSession) -> list[InventarioPacas]:
    result = await db.execute(select(InventarioPacas).order_by(InventarioPacas.material_id))
    return list(result.scalars().all())
