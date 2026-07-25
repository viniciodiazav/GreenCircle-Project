from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.detalle_salida.models import DetalleSalida
from app.modules.detalle_salida.schemas import DetalleSalidaCreate

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
    db: AsyncSession, movimiento_id: int | None = None
) -> list[tuple[DetalleSalida, int]]:
    stmt = (
        select(DetalleSalida, func.count(Paca.id))
        .outerjoin(Paca, Paca.detalle_salida_id == DetalleSalida.id)
        .group_by(DetalleSalida.id)
        .order_by(DetalleSalida.id)
    )
    if movimiento_id is not None:
        stmt = stmt.where(DetalleSalida.movimiento_id == movimiento_id)
    result = await db.execute(stmt)
    return [(fila[0], fila[1]) for fila in result.all()]


async def agregar_detalle_salida(data: DetalleSalidaCreate, db: AsyncSession) -> tuple[DetalleSalida, int]:
    movimiento: Movimiento = await get_movimiento_or_404(data.movimiento_id, db)
    validar_movimiento_para_detalle(movimiento, "SALIDA")

    cliente = await db.get(Cliente, data.cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cliente_id no existe")
    if not cliente.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cliente está inactivo")

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
        descripcion=data.descripcion,
    )
    db.add(detalle)
    await db.flush()

    for paca in pacas:
        paca.en_inventario = False
        paca.detalle_salida_id = detalle.id

    await db.commit()
    await db.refresh(detalle)
    return detalle, len(pacas)
