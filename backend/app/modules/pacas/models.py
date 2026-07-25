from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Paca(Base):
    __tablename__ = "pacas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    en_inventario: Mapped[bool] = mapped_column(default=True)
    fecha_registro: Mapped[datetime] = mapped_column(server_default=func.now())
    detalle_salida_id: Mapped[int | None] = mapped_column(ForeignKey("detalle_salida.id"))
