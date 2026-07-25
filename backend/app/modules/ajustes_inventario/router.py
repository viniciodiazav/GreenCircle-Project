from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.ajustes_inventario.schemas import AjusteInventarioCreate, AjusteInventarioOut
from app.modules.ajustes_inventario.service import crear_ajuste, listar_ajustes

router = APIRouter(prefix="/ajustes-inventario", tags=["ajustes-inventario"])


@router.get("", response_model=list[AjusteInventarioOut])
async def get_ajustes(
    material_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await listar_ajustes(db, material_id=material_id)


@router.post("", response_model=AjusteInventarioOut, status_code=status.HTTP_201_CREATED)
async def post_ajuste(data: AjusteInventarioCreate, db: AsyncSession = Depends(get_db)):
    return await crear_ajuste(data, db)
