from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ajustes_inventario.models import AjusteInventario
from app.modules.ajustes_inventario.schemas import AjusteInventarioCreate

# Cruce deliberado: hay que confirmar que el material exista antes de dejar
# registrar el ajuste, para poder devolver un 400 limpio en vez de que el
# error de FK burbujee crudo.
from app.modules.materiales.models import Material


async def listar_ajustes(db: AsyncSession, material_id: int | None = None) -> list[AjusteInventario]:
    stmt = select(AjusteInventario).order_by(AjusteInventario.fecha.desc())
    if material_id is not None:
        stmt = stmt.where(AjusteInventario.material_id == material_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def crear_ajuste(data: AjusteInventarioCreate, db: AsyncSession) -> AjusteInventario:
    material = await db.get(Material, data.material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="material_id no existe")

    ajuste = AjusteInventario(
        material_id=data.material_id,
        peso_ajuste=data.peso_ajuste,
        motivo=data.motivo,
        comentarios=data.comentarios,
    )
    db.add(ajuste)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ajuste dejaría el inventario de ese material en negativo",
        )
    await db.refresh(ajuste)
    return ajuste
