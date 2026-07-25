import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import engine, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    """Sesión ligada a una transacción que siempre se revierte al terminar
    el test -- así los tests corren contra la BD real (necesario porque
    triggers/constraints son de Postgres, no se pueden simular con sqlite)
    sin dejar ningún dato de prueba en ella."""
    # pytest-asyncio usa un event loop nuevo por test; el engine global vive
    # más que un solo test, así que hay que tirar el pool antes de conectar
    # para no reusar una conexión asyncpg atada a un loop ya cerrado.
    await engine.dispose()
    async with engine.connect() as connection:
        trans = await connection.begin()
        testing_session = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        session = testing_session()
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
