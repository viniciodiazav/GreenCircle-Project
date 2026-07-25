from datetime import datetime

from sqlalchemy import Computed, ForeignKey, ForeignKeyConstraint, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DetalleEntrada(Base):
    __tablename__ = "detalle_entrada"
    __table_args__ = (
        ForeignKeyConstraint(["movimiento_id", "tipo_movimiento"], ["movimientos.id", "movimientos.tipo"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movimiento_id: Mapped[int]
    tipo_movimiento: Mapped[str] = mapped_column(default="ENTRADA")
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"))
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    peso_bruto: Mapped[float] = mapped_column(Numeric(10, 2))
    tara: Mapped[float] = mapped_column(Numeric(10, 2))
    descuento: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    peso_neto: Mapped[float] = mapped_column(
        Numeric(10, 2), Computed("(peso_bruto - tara) * (1 - descuento / 100)")
    )
    precio_compra: Mapped[float | None] = mapped_column(Numeric(10, 2))
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    descripcion: Mapped[str | None]
    descripcion_descuento: Mapped[str | None]
