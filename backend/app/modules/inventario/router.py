from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.inventario.schemas import InventarioOut, InventarioPacasOut
from app.modules.inventario.service import listar_inventario, listar_inventario_pacas

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.get("", response_model=list[InventarioOut])
async def get_inventario(db: AsyncSession = Depends(get_db)):
    return await listar_inventario(db)


@router.get("/pacas", response_model=list[InventarioPacasOut])
async def get_inventario_pacas(db: AsyncSession = Depends(get_db)):
    return await listar_inventario_pacas(db)
