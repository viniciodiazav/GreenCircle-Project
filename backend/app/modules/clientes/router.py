from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.modules.clientes.schemas import ClienteCreate, ClienteOut, ClientePatch
from app.modules.clientes.service import (
    actualizar_cliente,
    crear_cliente,
    get_cliente_or_404,
    listar_clientes,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=PaginaOut[ClienteOut])
async def get_clientes(
    activo: bool | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    clientes, total = await listar_clientes(db, paginacion, activo=activo)
    return PaginaOut(items=clientes, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def post_cliente(data: ClienteCreate, db: AsyncSession = Depends(get_db)):
    return await crear_cliente(data, db)


@router.get("/{cliente_id}", response_model=ClienteOut)
async def get_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    return await get_cliente_or_404(cliente_id, db)


@router.patch("/{cliente_id}", response_model=ClienteOut)
async def patch_cliente(cliente_id: int, data: ClientePatch, db: AsyncSession = Depends(get_db)):
    return await actualizar_cliente(cliente_id, data, db)
