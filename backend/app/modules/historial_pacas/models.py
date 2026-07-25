from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HistorialPaca(Base):
    __tablename__ = "historial_pacas"

    id: Mapped[int] = mapped_column(primary_key=True)
    paca_id: Mapped[int] = mapped_column(ForeignKey("pacas.id", ondelete="CASCADE"))
    evento: Mapped[str]
    detalle_salida_id: Mapped[int | None] = mapped_column(ForeignKey("detalle_salida.id"))
    fecha: Mapped[datetime]
