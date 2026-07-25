from datetime import datetime

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HistorialPrecio(Base):
    __tablename__ = "historial_precios"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id", ondelete="CASCADE"))
    precio_anterior: Mapped[float] = mapped_column(Numeric(10, 2))
    precio_nuevo: Mapped[float] = mapped_column(Numeric(10, 2))
    fecha_cambio: Mapped[datetime]
