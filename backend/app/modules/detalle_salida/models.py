from datetime import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DetalleSalida(Base):
    __tablename__ = "detalle_salida"
    __table_args__ = (
        ForeignKeyConstraint(["movimiento_id", "tipo_movimiento"], ["movimientos.id", "movimientos.tipo"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movimiento_id: Mapped[int]
    tipo_movimiento: Mapped[str] = mapped_column(default="SALIDA")
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    precio_venta: Mapped[float] = mapped_column(Numeric(10, 2))
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    descripcion: Mapped[str | None]
