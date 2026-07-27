from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_usuario_actual
from app.core.pagination import Paginacion
from app.modules.detalle_salida.models import DetalleSalida
from app.modules.detalle_salida.schemas import DetalleSalidaCreate, DetalleSalidaPatch

# Cruce deliberado: para agregar una línea de salida hay que validar el
# movimiento al que pertenece (mismo patrón que detalle_entrada).
from app.modules.movimientos.models import Movimiento
from app.modules.movimientos.service import get_movimiento_or_404, validar_movimiento_para_detalle

# Cruce deliberado: vender pacas es, en una sola transacción, crear un
# detalle_salida y marcar esas pacas como vendidas. Partirlo en dos módulos
# sin este import dejaría abierta la posibilidad de un detalle_salida sin
# pacas o de pacas "vendidas" sin un detalle_salida real.
from app.modules.pacas.models import Paca

# Cruce deliberado: confirmar que el cliente siga activo antes de dejar
# registrar la venta (la BD ya lo garantiza vía trigger -- ver
# base-datos/movimientos/triggers.sql -- esto es solo para un 409 legible).
from app.modules.clientes.models import Cliente


async def get_detalle_salida_or_404(detalle_id: int, db: AsyncSession) -> tuple[DetalleSalida, int]:
    result = await db.execute(
        select(DetalleSalida, func.count(Paca.id))
        .outerjoin(Paca, Paca.detalle_salida_id == DetalleSalida.id)
        .where(DetalleSalida.id == detalle_id)
        .group_by(DetalleSalida.id)
    )
    fila = result.first()
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detalle de salida no encontrado")
    return fila[0], fila[1]


async def listar_detalle_salida(
    db: AsyncSession, paginacion: Paginacion, movimiento_id: int | None = None
) -> tuple[list[tuple[DetalleSalida, int]], int]:
    stmt = (
        select(DetalleSalida, func.count(Paca.id))
        .outerjoin(Paca, Paca.detalle_salida_id == DetalleSalida.id)
        .group_by(DetalleSalida.id)
        .order_by(DetalleSalida.id)
    )
    if movimiento_id is not None:
        stmt = stmt.where(DetalleSalida.movimiento_id == movimiento_id)
    # No usa ejecutar_paginado (app.core.pagination): esa fila no es un solo
    # modelo -- es (DetalleSalida, count(Paca.id)) -- así que no se puede
    # cerrar con result.scalars(); se cuenta y se pagina a mano.
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    result = await db.execute(stmt.limit(paginacion.limit).offset(paginacion.offset))
    return [(fila[0], fila[1]) for fila in result.all()], total or 0


async def agregar_detalle_salida(
    data: DetalleSalidaCreate, db: AsyncSession, usuario_id: int
) -> tuple[DetalleSalida, int]:
    movimiento: Movimiento = await get_movimiento_or_404(data.movimiento_id, db)
    validar_movimiento_para_detalle(movimiento, "SALIDA")

    cliente = await db.get(Cliente, data.cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cliente_id no existe")
    if not cliente.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cliente está inactivo")

    # Regla de negocio: todos los detalles de un mismo movimiento deben ser
    # del mismo cliente -- no se puede mezclar (la BD ya lo garantiza vía
    # trigger, esto es solo para un 409 legible antes de llegar a Postgres).
    cliente_existente = await db.scalar(
        select(DetalleSalida.cliente_id).where(DetalleSalida.movimiento_id == data.movimiento_id).limit(1)
    )
    if cliente_existente is not None and cliente_existente != data.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El movimiento ya tiene detalles del cliente {cliente_existente}, no puede mezclar clientes",
        )

    result = await db.execute(select(Paca).where(Paca.id.in_(data.pacas)))
    pacas = list(result.scalars().all())

    encontradas = {p.id for p in pacas}
    faltantes = sorted(set(data.pacas) - encontradas)
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pacas no encontradas: {faltantes}"
        )

    ya_vendidas = sorted(p.id for p in pacas if not p.en_inventario)
    if ya_vendidas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pacas ya vendidas, no están en inventario: {ya_vendidas}",
        )

    detalle = DetalleSalida(
        movimiento_id=data.movimiento_id,
        cliente_id=data.cliente_id,
        precio_venta=data.precio_venta,
        monto_total=data.monto_total,
        descripcion=data.descripcion,
        creado_por=usuario_id,
    )
    db.add(detalle)
    await db.flush()

    for paca in pacas:
        paca.en_inventario = False
        paca.detalle_salida_id = detalle.id

    await db.commit()
    await db.refresh(detalle)
    return detalle, len(pacas)


async def actualizar_detalle_salida(
    detalle_id: int, data: DetalleSalidaPatch, db: AsyncSession
) -> tuple[DetalleSalida, int]:
    """Corrige precio_venta/monto_total/descripcion -- solo mientras el
    movimiento sigue abierto. Sin efecto lateral (no toca pacas ni
    inventario), a diferencia de detalle_entrada."""
    detalle, cantidad = await get_detalle_salida_or_404(detalle_id, db)
    movimiento = await get_movimiento_or_404(detalle.movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento ya está cerrado, no se pueden editar sus detalles",
        )

    if data.precio_venta is not None:
        detalle.precio_venta = data.precio_venta
    if data.monto_total is not None:
        detalle.monto_total = data.monto_total
    if data.descripcion is not None:
        detalle.descripcion = data.descripcion

    await db.commit()
    await db.refresh(detalle)
    return detalle, cantidad


async def cancelar_detalle_salida(detalle_id: int, db: AsyncSession, usuario_id: int) -> None:
    """Cancela (borra) una venta capturada por error -- solo mientras el
    movimiento sigue abierto. Un trigger en BD libera las pacas vendidas
    (en_inventario = true, detalle_salida_id = NULL) antes de borrar la fila
    (ver liberar_pacas_al_cancelar_detalle_salida en
    base-datos/movimientos/triggers.sql), lo que en cadena reactiva
    inventario_pacas y anota un evento CANCELACION en historial_pacas."""
    detalle, _ = await get_detalle_salida_or_404(detalle_id, db)
    movimiento = await get_movimiento_or_404(detalle.movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento ya está cerrado, no se pueden cancelar sus detalles",
        )

    # trg_liberar_pacas_al_cancelar_detalle_salida -> trg_historial_paca_cancelacion
    # leen esto para anotar quién canceló en historial_pacas.
    await set_usuario_actual(db, usuario_id)
    await db.delete(detalle)
    await db.commit()
