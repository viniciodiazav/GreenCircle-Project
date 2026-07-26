from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TicketVenta(Base):
    __tablename__ = "ticket_venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("movimientos.id"), unique=True)
    # folio lo arma un trigger de Postgres (ver base-datos/tickets/triggers.sql),
    # igual que el código de pacas -- nunca se manda desde el backend.
    folio: Mapped[str] = mapped_column(unique=True)
    cliente: Mapped[str]
    cantidad_pacas: Mapped[int]
    materiales: Mapped[list[str]] = mapped_column(ARRAY(String))
    fecha: Mapped[datetime]
