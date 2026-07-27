from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Movimiento(Base):
    __tablename__ = "movimientos"
    __table_args__ = (UniqueConstraint("id", "tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str]
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    cerrado: Mapped[bool] = mapped_column(default=False)
    descripcion: Mapped[str | None]
    # Nullable: registros creados antes de que la autenticación existiera no
    # tienen autor conocido.
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
