from datetime import datetime

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HistorialKg(Base):
    __tablename__ = "historial_kg"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    peso_anterior: Mapped[float] = mapped_column(Numeric(12, 2))
    peso_nuevo: Mapped[float] = mapped_column(Numeric(12, 2))
    fecha_cambio: Mapped[datetime]
    # Solo se llena en cancelaciones (revertir_inventario_entrada_cancelada) --
    # los demás triggers que insertan aquí no cambian, quedan NULL.
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
