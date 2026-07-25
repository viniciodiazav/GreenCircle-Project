from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.detalle_entrada.models import DetalleEntrada
from app.modules.detalle_entrada.schemas import DetalleEntradaCreate

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


async def listar_detalle_entrada(db: AsyncSession, movimiento_id: int | None = None) -> list[DetalleEntrada]:
    stmt = select(DetalleEntrada).order_by(DetalleEntrada.id)
    if movimiento_id is not None:
        stmt = stmt.where(DetalleEntrada.movimiento_id == movimiento_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


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

    detalle = DetalleEntrada(
        movimiento_id=data.movimiento_id,
        proveedor_id=data.proveedor_id,
        material_id=data.material_id,
        peso_bruto=data.peso_bruto,
        tara=data.tara,
        descuento=data.descuento,
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
