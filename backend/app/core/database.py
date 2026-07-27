from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def set_usuario_actual(db: AsyncSession, usuario_id: int) -> None:
    """Le dice a la sesión de Postgres quién es el usuario actual, para que
    los triggers de auditoría de cancelaciones (historial_kg, historial_pacas
    -- ver base-datos/inventario/triggers.sql y base-datos/pacas/triggers.sql)
    puedan anotarlo. SET LOCAL: solo dura la transacción actual.

    SET no acepta parámetros bind ($1) -- Postgres lo rechaza con error de
    sintaxis, tiene que ir como literal en el texto del SQL. `usuario_id` sale
    del JWT ya decodificado (int), nunca de un body de request, así que el
    int() de abajo es solo una segunda capa de defensa, no la única."""
    await db.execute(text(f"SET LOCAL app.usuario_actual = '{int(usuario_id)}'"))
