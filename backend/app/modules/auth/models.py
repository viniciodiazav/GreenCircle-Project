from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column


class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
