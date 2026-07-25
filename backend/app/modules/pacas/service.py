from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pacas.models import Paca
from app.modules.pacas.schemas import PacaCreate


async def get_paca_or_404(paca_id: int, db: AsyncSession) -> Paca:
    paca = await db.get(Paca, paca_id)
    if paca is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paca no encontrada")
    return paca


async def listar_pacas(db: AsyncSession, en_inventario: bool | None = None) -> list[Paca]:
    stmt = select(Paca).order_by(Paca.fecha_registro.desc())
    if en_inventario is not None:
        stmt = stmt.where(Paca.en_inventario.is_(en_inventario))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def registrar_paca(data: PacaCreate, db: AsyncSession) -> Paca:
    paca = Paca(codigo=data.codigo, material_id=data.material_id)
    db.add(paca)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una paca con ese código, o material_id no existe",
        )
    await db.refresh(paca)
    return paca
