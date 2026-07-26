from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.tickets_venta.models import TicketVenta


async def get_ticket_venta_or_404(ticket_id: int, db: AsyncSession) -> TicketVenta:
    ticket = await db.get(TicketVenta, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket de venta no encontrado")
    return ticket


async def listar_tickets_venta(
    db: AsyncSession, paginacion: Paginacion, movimiento_id: int | None = None
) -> tuple[list[TicketVenta], int]:
    stmt = select(TicketVenta).order_by(TicketVenta.fecha.desc())
    if movimiento_id is not None:
        stmt = stmt.where(TicketVenta.movimiento_id == movimiento_id)
    return await ejecutar_paginado(stmt, db, paginacion)
