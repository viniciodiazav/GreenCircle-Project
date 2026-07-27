from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AjusteInventario(Base):
    __tablename__ = "ajustes_inventario"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    peso_ajuste: Mapped[float] = mapped_column(Numeric(12, 2))
    motivo: Mapped[str]
    comentarios: Mapped[str | None]
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
