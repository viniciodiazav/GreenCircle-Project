from datetime import datetime

from sqlalchemy import Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Material(Base):
    __tablename__ = "materiales"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(unique=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    unidad: Mapped[str] = mapped_column(default="kg")
    precio_actual: Mapped[float] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = mapped_column(default=True)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now())
