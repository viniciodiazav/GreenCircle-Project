from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.clientes.schemas import ClienteCreate, ClienteOut, ClientePatch
from app.modules.clientes.service import (
    actualizar_cliente,
    crear_cliente,
    get_cliente_or_404,
    listar_clientes,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
async def get_clientes(
    activo: bool | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_clientes(db, activo=activo)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def post_cliente(data: ClienteCreate, db: AsyncSession = Depends(get_db)):
    return await crear_cliente(data, db)


@router.get("/{cliente_id}", response_model=ClienteOut)
async def get_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    return await get_cliente_or_404(cliente_id, db)


@router.patch("/{cliente_id}", response_model=ClienteOut)
async def patch_cliente(cliente_id: int, data: ClientePatch, db: AsyncSession = Depends(get_db)):
    return await actualizar_cliente(cliente_id, data, db)
