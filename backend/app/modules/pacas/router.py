from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.pacas.schemas import PacaCreate, PacaOut
from app.modules.pacas.service import get_paca_or_404, listar_pacas, registrar_paca

router = APIRouter(prefix="/pacas", tags=["pacas"])


@router.get("", response_model=list[PacaOut])
async def get_pacas(
    en_inventario: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await listar_pacas(db, en_inventario=en_inventario)


@router.post("", response_model=PacaOut, status_code=status.HTTP_201_CREATED)
async def post_paca(data: PacaCreate, db: AsyncSession = Depends(get_db)):
    return await registrar_paca(data, db)


@router.get("/{paca_id}", response_model=PacaOut)
async def get_paca(paca_id: int, db: AsyncSession = Depends(get_db)):
    return await get_paca_or_404(paca_id, db)
