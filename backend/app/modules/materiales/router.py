from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginaOut, Paginacion, parametros_paginacion
from app.core.security import get_current_user, require_admin
from app.modules.materiales.schemas import (
    MaterialCreate,
    MaterialOut,
    MaterialPatch,
    MaterialPublicOut,
)
from app.modules.materiales.service import (
    actualizar_material,
    crear_material,
    listar_materiales,
)

# GET "" (público) es intencional: es el listado de precios que ve cualquiera
# en la app móvil sin loguearse (ver app-movil/src/screens/HomeScreen.tsx).
# GET /admin* es de cualquier usuario logueado (operador lo necesita para
# elegir material_id al capturar detalles). Crear/editar (incluye precio y
# activo) es exclusivo de administrador -- ver ../../../base-datos/README.md.
router = APIRouter(prefix="/materiales", tags=["materiales"])


@router.get("", response_model=PaginaOut[MaterialPublicOut])
async def get_materiales_publico(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    materiales, total = await listar_materiales(db, paginacion, solo_activos=True)
    items = [MaterialPublicOut(nombre=m.nombre, precio=m.precio_actual) for m in materiales]
    return PaginaOut(items=items, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.get("/admin", response_model=PaginaOut[MaterialOut], dependencies=[Depends(get_current_user)])
async def get_materiales_admin_todos(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    materiales, total = await listar_materiales(db, paginacion, solo_activos=False)
    return PaginaOut(items=materiales, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.get(
    "/admin/activos", response_model=PaginaOut[MaterialOut], dependencies=[Depends(get_current_user)]
)
async def get_materiales_admin_activos(
    paginacion: Paginacion = Depends(parametros_paginacion), db: AsyncSession = Depends(get_db)
):
    materiales, total = await listar_materiales(db, paginacion, solo_activos=True)
    return PaginaOut(items=materiales, total=total, limit=paginacion.limit, offset=paginacion.offset)


@router.post(
    "",
    response_model=MaterialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def post_material(data: MaterialCreate, db: AsyncSession = Depends(get_db)):
    return await crear_material(data, db)


@router.patch(
    "/{material_id}", response_model=MaterialOut, dependencies=[Depends(require_admin)]
)
async def patch_material(
    material_id: int, data: MaterialPatch, db: AsyncSession = Depends(get_db)
):
    return await actualizar_material(material_id, data, db)
