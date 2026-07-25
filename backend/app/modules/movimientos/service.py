from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.movimientos.models import Movimiento
from app.modules.movimientos.schemas import MovimientoCreate


async def get_movimiento_or_404(movimiento_id: int, db: AsyncSession) -> Movimiento:
    movimiento = await db.get(Movimiento, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")
    return movimiento


async def listar_movimientos(db: AsyncSession, tipo: str | None = None) -> list[Movimiento]:
    stmt = select(Movimiento).order_by(Movimiento.fecha.desc())
    if tipo is not None:
        stmt = stmt.where(Movimiento.tipo == tipo)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def crear_movimiento(data: MovimientoCreate, db: AsyncSession) -> Movimiento:
    movimiento = Movimiento(tipo=data.tipo, descripcion=data.descripcion)
    db.add(movimiento)
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


def validar_movimiento_para_detalle(movimiento: Movimiento, tipo_esperado: str) -> None:
    """Usada por detalle_entrada/detalle_salida antes de agregar una línea."""
    if movimiento.tipo != tipo_esperado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El movimiento no es de tipo {tipo_esperado}",
        )
    if movimiento.cerrado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El movimiento ya está cerrado")


async def cerrar_movimiento(movimiento_id: int, db: AsyncSession) -> Movimiento:
    movimiento = await get_movimiento_or_404(movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El movimiento ya está cerrado")
    movimiento.cerrado = True
    await db.commit()
    await db.refresh(movimiento)
    return movimiento
