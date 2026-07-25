from datetime import datetime

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Inventario(Base):
    __tablename__ = "inventario"

    material_id: Mapped[int] = mapped_column(primary_key=True)
    peso_total: Mapped[float] = mapped_column(Numeric(12, 2))
    actualizado_en: Mapped[datetime]


class InventarioPacas(Base):
    __tablename__ = "inventario_pacas"

    material_id: Mapped[int] = mapped_column(primary_key=True)
    cantidad: Mapped[int]
    actualizado_en: Mapped[datetime]
