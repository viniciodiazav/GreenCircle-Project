from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clientes.models import Cliente
from app.modules.clientes.schemas import ClienteCreate, ClientePatch


async def get_cliente_or_404(cliente_id: int, db: AsyncSession) -> Cliente:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


async def listar_clientes(db: AsyncSession, activo: bool | None = None) -> list[Cliente]:
    stmt = select(Cliente).order_by(Cliente.nombre)
    if activo is not None:
        stmt = stmt.where(Cliente.activo.is_(activo))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def crear_cliente(data: ClienteCreate, db: AsyncSession) -> Cliente:
    cliente = Cliente(nombre=data.nombre, direccion=data.direccion, contacto=data.contacto)
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente


async def actualizar_cliente(cliente_id: int, data: ClientePatch, db: AsyncSession) -> Cliente:
    cliente = await get_cliente_or_404(cliente_id, db)
    if data.nombre is not None:
        cliente.nombre = data.nombre
    if data.direccion is not None:
        cliente.direccion = data.direccion
    if data.contacto is not None:
        cliente.contacto = data.contacto
    if data.activo is not None:
        cliente.activo = data.activo

    await db.commit()
    await db.refresh(cliente)
    return cliente
