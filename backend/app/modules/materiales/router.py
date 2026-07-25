from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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

# Sin autenticación por ahora en ninguna ruta (decisión explícita del usuario,
# 2026-07-25): la app móvil y "el sistema" van a tener esquemas de login
# distintos y ninguno de los dos está definido todavía.
#
# Solo materiales aquí -- el historial de precios vive en su propio router
# (app.modules.historial_precios), no anidado bajo /materiales.
router = APIRouter(prefix="/materiales", tags=["materiales"])


@router.get("", response_model=list[MaterialPublicOut])
async def get_materiales_publico(db: AsyncSession = Depends(get_db)):
    materiales = await listar_materiales(db, solo_activos=True)
    return [MaterialPublicOut(nombre=m.nombre, precio=m.precio_actual) for m in materiales]


@router.get("/admin", response_model=list[MaterialOut])
async def get_materiales_admin_todos(db: AsyncSession = Depends(get_db)):
    return await listar_materiales(db, solo_activos=False)


@router.get("/admin/activos", response_model=list[MaterialOut])
async def get_materiales_admin_activos(db: AsyncSession = Depends(get_db)):
    return await listar_materiales(db, solo_activos=True)


@router.post("", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
async def post_material(data: MaterialCreate, db: AsyncSession = Depends(get_db)):
    return await crear_material(data, db)


@router.patch("/{material_id}", response_model=MaterialOut)
async def patch_material(
    material_id: int, data: MaterialPatch, db: AsyncSession = Depends(get_db)
):
    return await actualizar_material(material_id, data, db)
