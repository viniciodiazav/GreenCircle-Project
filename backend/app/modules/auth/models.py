from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    activo: Mapped[bool] = mapped_column(default=True)
    rol: Mapped[str] = mapped_column(default="operador")
