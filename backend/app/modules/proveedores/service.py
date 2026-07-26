from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.proveedores.models import Proveedor
from app.modules.proveedores.schemas import ProveedorCreate, ProveedorPatch


async def get_proveedor_or_404(proveedor_id: int, db: AsyncSession) -> Proveedor:
    proveedor = await db.get(Proveedor, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return proveedor


async def listar_proveedores(
    db: AsyncSession, paginacion: Paginacion, activo: bool | None = None
) -> tuple[list[Proveedor], int]:
    stmt = select(Proveedor).order_by(Proveedor.nombre)
    if activo is not None:
        stmt = stmt.where(Proveedor.activo.is_(activo))
    return await ejecutar_paginado(stmt, db, paginacion)


async def crear_proveedor(data: ProveedorCreate, db: AsyncSession) -> Proveedor:
    proveedor = Proveedor(nombre=data.nombre, direccion=data.direccion, contacto=data.contacto)
    db.add(proveedor)
    await db.commit()
    await db.refresh(proveedor)
    return proveedor


async def actualizar_proveedor(proveedor_id: int, data: ProveedorPatch, db: AsyncSession) -> Proveedor:
    proveedor = await get_proveedor_or_404(proveedor_id, db)
    if data.nombre is not None:
        proveedor.nombre = data.nombre
    if data.direccion is not None:
        proveedor.direccion = data.direccion
    if data.contacto is not None:
        proveedor.contacto = data.contacto
    if data.activo is not None:
        proveedor.activo = data.activo

    await db.commit()
    await db.refresh(proveedor)
    return proveedor
