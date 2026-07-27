import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.core.database import Base
from app.modules.ajustes_inventario.models import AjusteInventario  # noqa: F401
from app.modules.auth.models import Usuario  # noqa: F401  (registra metadata)
from app.modules.clientes.models import Cliente  # noqa: F401
from app.modules.detalle_entrada.models import DetalleEntrada  # noqa: F401
from app.modules.detalle_salida.models import DetalleSalida  # noqa: F401
from app.modules.historial_kg.models import HistorialKg  # noqa: F401
from app.modules.historial_pacas.models import HistorialPaca  # noqa: F401
from app.modules.historial_precios.models import HistorialPrecio  # noqa: F401
from app.modules.inventario.models import Inventario, InventarioPacas  # noqa: F401
from app.modules.materiales.models import Material  # noqa: F401
from app.modules.movimientos.models import Movimiento  # noqa: F401
from app.modules.pacas.models import Paca  # noqa: F401
from app.modules.proveedores.models import Proveedor  # noqa: F401
from app.modules.tickets_compra.models import TicketCompra  # noqa: F401
from app.modules.tickets_venta.models import TicketVenta  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
