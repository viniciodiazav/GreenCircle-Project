from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.inventario.models import Inventario, InventarioPacas


async def listar_inventario(db: AsyncSession, paginacion: Paginacion) -> tuple[list[Inventario], int]:
    stmt = select(Inventario).order_by(Inventario.material_id)
    return await ejecutar_paginado(stmt, db, paginacion)


async def listar_inventario_pacas(
    db: AsyncSession, paginacion: Paginacion
) -> tuple[list[InventarioPacas], int]:
    stmt = select(InventarioPacas).order_by(InventarioPacas.material_id)
    return await ejecutar_paginado(stmt, db, paginacion)
