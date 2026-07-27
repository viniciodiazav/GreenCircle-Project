from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import get_current_user
from app.modules.inventario.schemas import InventarioOut, InventarioPacasOut
from app.modules.inventario.service import listar_inventario, listar_inventario_pacas

router = APIRouter(prefix="/inventario", tags=["inventario"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginaOut[InventarioOut])
async def get_inventario(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    items, total = await listar_inventario(db, paginacion)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.get("/pacas", response_model=PaginaOut[InventarioPacasOut])
async def get_inventario_pacas(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    items, total = await listar_inventario_pacas(db, paginacion)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)
