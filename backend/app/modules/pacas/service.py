from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pacas.models import Paca
from app.modules.pacas.schemas import PacaCreate

# Cruce deliberado: confirmar que el material siga activo antes de dejar
# registrar la paca (la BD ya lo garantiza vía trigger -- ver
# base-datos/pacas/triggers.sql -- esto es solo para un 409 legible).
from app.modules.materiales.models import Material


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
    material = await db.get(Material, data.material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="material_id no existe")
    if not material.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El material está inactivo")

    paca = Paca(material_id=data.material_id, peso=data.peso)
    db.add(paca)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo generar un código único para la paca, intenta de nuevo",
        )
    await db.refresh(paca)
    return paca
