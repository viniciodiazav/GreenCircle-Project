from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.modules.tickets_compra.schemas import TicketCompraOut
from app.modules.tickets_compra.service import get_ticket_compra_or_404, listar_tickets_compra

router = APIRouter(prefix="/tickets-compra", tags=["tickets-compra"])


@router.get("", response_model=PaginaOut[TicketCompraOut])
async def get_tickets_compra(
    movimiento_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_tickets_compra(db, paginacion, movimiento_id=movimiento_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.get("/{ticket_id}", response_model=TicketCompraOut)
async def get_ticket_compra(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_compra_or_404(ticket_id, db)
