from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.movimientos.models import Movimiento
from app.modules.movimientos.schemas import MovimientoCreate, MovimientoPatch

# Cruce deliberado: para bloquear el cierre de un movimiento sin detalles hay
# que poder consultar detalle_entrada o detalle_salida según el tipo -- ver
# cerrar_movimiento() abajo. Estos modelos no importan de vuelta a
# movimientos.service, así que no hay ciclo.
from app.modules.detalle_entrada.models import DetalleEntrada
from app.modules.detalle_salida.models import DetalleSalida


async def get_movimiento_or_404(movimiento_id: int, db: AsyncSession) -> Movimiento:
    movimiento = await db.get(Movimiento, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")
    return movimiento


async def listar_movimientos(
    db: AsyncSession, paginacion: Paginacion, tipo: str | None = None
) -> tuple[list[Movimiento], int]:
    stmt = select(Movimiento).order_by(Movimiento.fecha.desc())
    if tipo is not None:
        stmt = stmt.where(Movimiento.tipo == tipo)
    return await ejecutar_paginado(stmt, db, paginacion)


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

    # Un movimiento sin detalles no puede cerrarse -- no habría de dónde
    # sacar el proveedor/cliente ni los materiales para su ticket (ver
    # base-datos/tickets/triggers.sql, que genera el ticket al cerrar). La BD
    # ya lo garantiza vía trigger (base-datos/movimientos/triggers.sql); esto
    # es solo para un 409 legible en vez de dejar burbujear la excepción cruda.
    modelo_detalle = DetalleEntrada if movimiento.tipo == "ENTRADA" else DetalleSalida
    tiene_detalles = await db.scalar(
        select(modelo_detalle.id).where(modelo_detalle.movimiento_id == movimiento_id).limit(1)
    )
    if tiene_detalles is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento no tiene detalles, no se puede cerrar",
        )

    movimiento.cerrado = True
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


async def actualizar_movimiento(movimiento_id: int, data: MovimientoPatch, db: AsyncSession) -> Movimiento:
    """Solo edita descripcion -- tipo no se puede cambiar (rompería la FK
    compuesta con detalle_entrada/detalle_salida) y no tiene otro efecto
    lateral, así que se permite en cualquier momento (abierto o cerrado)."""
    movimiento = await get_movimiento_or_404(movimiento_id, db)
    movimiento.descripcion = data.descripcion
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


async def cancelar_movimiento(movimiento_id: int, db: AsyncSession) -> None:
    """Cancela (borra) un movimiento vacío y abierto -- creado por error, sin
    ningún detalle todavía. Si ya tiene detalles, hay que cancelarlos uno por
    uno primero (DELETE /detalle-entrada/{id} o /detalle-salida/{id}) antes
    de poder cancelar el movimiento: cada cancelación de detalle revierte su
    propio efecto lateral (inventario, pacas), así que no se puede "cancelar
    todo de un jalón" sin pasar por ahí."""
    movimiento = await get_movimiento_or_404(movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El movimiento ya está cerrado")

    modelo_detalle = DetalleEntrada if movimiento.tipo == "ENTRADA" else DetalleSalida
    tiene_detalles = await db.scalar(
        select(modelo_detalle.id).where(modelo_detalle.movimiento_id == movimiento_id).limit(1)
    )
    if tiene_detalles is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento tiene detalles, cancélalos primero antes de cancelar el movimiento",
        )

    await db.delete(movimiento)
    await db.commit()
