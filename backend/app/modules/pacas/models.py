from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Paca(Base):
    __tablename__ = "pacas"

    id: Mapped[int] = mapped_column(primary_key=True)
    # codigo lo arma un trigger de Postgres (ver base-datos/pacas/triggers.sql)
    # a partir del código del material + fecha + correlativo del día -- nunca
    # se manda desde el backend, por eso no tiene default aquí: al no setear
    # el atributo en Python, SQLAlchemy lo omite del INSERT y deja que el
    # trigger lo rellene antes de que se evalúe el NOT NULL.
    codigo: Mapped[str] = mapped_column(unique=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    peso: Mapped[float] = mapped_column(Numeric(10, 2))
    en_inventario: Mapped[bool] = mapped_column(default=True)
    fecha_registro: Mapped[datetime] = mapped_column(server_default=func.now())
    detalle_salida_id: Mapped[int | None] = mapped_column(ForeignKey("detalle_salida.id"))
