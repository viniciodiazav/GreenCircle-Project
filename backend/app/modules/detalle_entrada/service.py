from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.detalle_entrada.models import DetalleEntrada
from app.modules.detalle_entrada.schemas import DetalleEntradaCreate, DetalleEntradaPatch

# Cruce deliberado (igual que en pacas/movimientos): para agregar una línea
# de entrada hay que validar el tipo y el estado del movimiento al que
# pertenece, así que se importa el modelo y la validación ya existente de
# movimientos en vez de duplicarla.
from app.modules.movimientos.models import Movimiento
from app.modules.movimientos.service import get_movimiento_or_404, validar_movimiento_para_detalle

# Cruce deliberado: hay que confirmar que el proveedor y el material sigan
# activos antes de dejar registrar la línea (la BD ya lo garantiza vía
# trigger -- ver base-datos/movimientos/triggers.sql -- esto es solo para dar
# un 409 legible en vez de dejar que la excepción cruda de Postgres burbujee).
from app.modules.materiales.models import Material
from app.modules.proveedores.models import Proveedor


async def get_detalle_entrada_or_404(detalle_id: int, db: AsyncSession) -> DetalleEntrada:
    detalle = await db.get(DetalleEntrada, detalle_id)
    if detalle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detalle de entrada no encontrado")
    return detalle


async def listar_detalle_entrada(
    db: AsyncSession, paginacion: Paginacion, movimiento_id: int | None = None
) -> tuple[list[DetalleEntrada], int]:
    stmt = select(DetalleEntrada).order_by(DetalleEntrada.id)
    if movimiento_id is not None:
        stmt = stmt.where(DetalleEntrada.movimiento_id == movimiento_id)
    return await ejecutar_paginado(stmt, db, paginacion)


async def agregar_detalle_entrada(data: DetalleEntradaCreate, db: AsyncSession) -> DetalleEntrada:
    movimiento: Movimiento = await get_movimiento_or_404(data.movimiento_id, db)
    validar_movimiento_para_detalle(movimiento, "ENTRADA")

    proveedor = await db.get(Proveedor, data.proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="proveedor_id no existe")
    if not proveedor.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El proveedor está inactivo")

    material = await db.get(Material, data.material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="material_id no existe")
    if not material.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El material está inactivo")

    # Regla de negocio: todos los detalles de un mismo movimiento deben ser
    # del mismo proveedor -- no se puede mezclar (la BD ya lo garantiza vía
    # trigger, esto es solo para un 409 legible antes de llegar a Postgres).
    proveedor_existente = await db.scalar(
        select(DetalleEntrada.proveedor_id).where(DetalleEntrada.movimiento_id == data.movimiento_id).limit(1)
    )
    if proveedor_existente is not None and proveedor_existente != data.proveedor_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El movimiento ya tiene detalles del proveedor {proveedor_existente}, no puede mezclar proveedores",
        )

    detalle = DetalleEntrada(
        movimiento_id=data.movimiento_id,
        proveedor_id=data.proveedor_id,
        material_id=data.material_id,
        peso_bruto=data.peso_bruto,
        tara=data.tara,
        descuento=data.descuento,
        monto_total=data.monto_total,
        descripcion=data.descripcion,
        descripcion_descuento=data.descripcion_descuento,
    )
    db.add(detalle)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="peso_bruto debe ser mayor que tara",
        )
    await db.refresh(detalle)
    return detalle


async def actualizar_detalle_entrada(
    detalle_id: int, data: DetalleEntradaPatch, db: AsyncSession
) -> DetalleEntrada:
    """Corrige peso_bruto/tara/descuento/monto_total/descripcion de una línea
    -- solo mientras el movimiento sigue abierto. peso_neto se recalcula solo
    (columna GENERATED) y un trigger en BD aplica el delta resultante al
    inventario (ver base-datos/inventario/triggers.sql,
    sincronizar_inventario_entrada_editada)."""
    detalle = await get_detalle_entrada_or_404(detalle_id, db)
    movimiento = await get_movimiento_or_404(detalle.movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento ya está cerrado, no se pueden editar sus detalles",
        )

    if data.peso_bruto is not None:
        detalle.peso_bruto = data.peso_bruto
    if data.tara is not None:
        detalle.tara = data.tara
    if data.descuento is not None:
        detalle.descuento = data.descuento
    if data.monto_total is not None:
        detalle.monto_total = data.monto_total
    if data.descripcion is not None:
        detalle.descripcion = data.descripcion
    if data.descripcion_descuento is not None:
        detalle.descripcion_descuento = data.descripcion_descuento

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "detalle_entrada_check" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="peso_bruto debe ser mayor que tara",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La corrección dejaría el inventario de ese material en negativo "
            "(ya se compactó una paca con ese material)",
        )
    await db.refresh(detalle)
    return detalle


async def cancelar_detalle_entrada(detalle_id: int, db: AsyncSession) -> None:
    """Cancela (borra) una línea capturada por error -- solo mientras el
    movimiento sigue abierto. Un trigger en BD revierte lo que había sumado
    al inventario (ver revertir_inventario_entrada_cancelada); si ese
    material ya se compactó en una paca, el CHECK de inventario rechaza la
    cancelación (no se puede cancelar una entrada cuyo material ya se usó)."""
    detalle = await get_detalle_entrada_or_404(detalle_id, db)
    movimiento = await get_movimiento_or_404(detalle.movimiento_id, db)
    if movimiento.cerrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El movimiento ya está cerrado, no se pueden cancelar sus detalles",
        )

    await db.delete(detalle)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar: el inventario de ese material ya se usó "
            "(ej. se compactó una paca) y revertir lo dejaría en negativo",
        )
