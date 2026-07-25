from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    direccion: Mapped[str | None]
    contacto: Mapped[str | None]
    activo: Mapped[bool] = mapped_column(default=True)
