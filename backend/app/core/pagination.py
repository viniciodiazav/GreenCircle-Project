from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class Paginacion(BaseModel):
    limit: int
    offset: int


def parametros_paginacion(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Paginacion:
    return Paginacion(limit=limit, offset=offset)


class PaginaOut(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


async def ejecutar_paginado(
    stmt: Select, db: AsyncSession, paginacion: Paginacion
) -> tuple[Sequence, int]:
    """Corre stmt (sin limit/offset) para contar el total, y de nuevo con
    limit/offset para la página pedida. select_from(stmt.subquery()) cuenta
    bien incluso con joins/group_by (ej. detalle_salida + count de pacas)."""
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    result = await db.execute(stmt.limit(paginacion.limit).offset(paginacion.offset))
    return result.scalars().all(), total or 0
