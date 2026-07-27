from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import UsuarioActual, get_current_user
from app.modules.detalle_salida.schemas import (
    DetalleSalidaCreate,
    DetalleSalidaOut,
    DetalleSalidaPatch,
)
from app.modules.detalle_salida.service import (
    actualizar_detalle_salida,
    agregar_detalle_salida,
    cancelar_detalle_salida,
    get_detalle_salida_or_404,
    listar_detalle_salida,
)

router = APIRouter(
    prefix="/detalle-salida", tags=["detalle-salida"], dependencies=[Depends(get_current_user)]
)


def _a_schema(detalle, cantidad_pacas: int) -> DetalleSalidaOut:
    return DetalleSalidaOut(
        id=detalle.id,
        movimiento_id=detalle.movimiento_id,
        cliente_id=detalle.cliente_id,
        precio_venta=detalle.precio_venta,
        monto_total=detalle.monto_total,
        fecha=detalle.fecha,
        descripcion=detalle.descripcion,
        cantidad_pacas=cantidad_pacas,
        creado_por=detalle.creado_por,
    )


@router.get("", response_model=PaginaOut[DetalleSalidaOut])
async def get_detalles_salida(
    movimiento_id: int | None = Query(default=None),
    paginacion: Paginacion = Depends(parametros_paginacion),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await listar_detalle_salida(db, paginacion, movimiento_id=movimiento_id)
    items = [_a_schema(detalle, cantidad) for detalle, cantidad in filas]
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post("", response_model=DetalleSalidaOut, status_code=status.HTTP_201_CREATED)
async def post_detalle_salida(
    data: DetalleSalidaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    detalle, cantidad = await agregar_detalle_salida(data, db, usuario.id)
    return _a_schema(detalle, cantidad)


@router.get("/{detalle_id}", response_model=DetalleSalidaOut)
async def get_detalle_salida(detalle_id: int, db: AsyncSession = Depends(get_db)):
    detalle, cantidad = await get_detalle_salida_or_404(detalle_id, db)
    return _a_schema(detalle, cantidad)


@router.patch("/{detalle_id}", response_model=DetalleSalidaOut)
async def patch_detalle_salida(
    detalle_id: int, data: DetalleSalidaPatch, db: AsyncSession = Depends(get_db)
):
    detalle, cantidad = await actualizar_detalle_salida(detalle_id, data, db)
    return _a_schema(detalle, cantidad)


@router.delete("/{detalle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detalle_salida(
    detalle_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    await cancelar_detalle_salida(detalle_id, db, usuario.id)
