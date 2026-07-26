from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.modules.tickets_venta.schemas import TicketVentaOut
from app.modules.tickets_venta.service import get_ticket_venta_or_404, listar_tickets_venta

router = APIRouter(prefix="/tickets-venta", tags=["tickets-venta"])


@router.get("", response_model=PaginaOut[TicketVentaOut])
async def get_tickets_venta(
    movimiento_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    items, total = await listar_tickets_venta(db, paginacion, movimiento_id=movimiento_id)
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.get("/{ticket_id}", response_model=TicketVentaOut)
async def get_ticket_venta(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_venta_or_404(ticket_id, db)
