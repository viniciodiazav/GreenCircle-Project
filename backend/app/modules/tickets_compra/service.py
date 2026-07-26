from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.tickets_compra.models import TicketCompra


async def get_ticket_compra_or_404(ticket_id: int, db: AsyncSession) -> TicketCompra:
    ticket = await db.get(TicketCompra, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket de compra no encontrado")
    return ticket


async def listar_tickets_compra(
    db: AsyncSession, paginacion: Paginacion, movimiento_id: int | None = None
) -> tuple[list[TicketCompra], int]:
    stmt = select(TicketCompra).order_by(TicketCompra.fecha.desc())
    if movimiento_id is not None:
        stmt = stmt.where(TicketCompra.movimiento_id == movimiento_id)
    return await ejecutar_paginado(stmt, db, paginacion)
