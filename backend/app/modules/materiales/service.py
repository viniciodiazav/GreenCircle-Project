from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.modules.materiales.codigo import generar_codigo_base
from app.modules.materiales.models import Material
from app.modules.materiales.schemas import MaterialCreate, MaterialPatch


async def get_material_or_404(material_id: int, db: AsyncSession) -> Material:
    material = await db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material no encontrado")
    return material


async def listar_materiales(
    db: AsyncSession, paginacion: Paginacion, solo_activos: bool = True
) -> tuple[list[Material], int]:
    stmt = select(Material).order_by(Material.nombre)
    if solo_activos:
        stmt = stmt.where(Material.activo.is_(True))
    return await ejecutar_paginado(stmt, db, paginacion)


async def _codigo_disponible(codigo: str, db: AsyncSession) -> bool:
    result = await db.execute(select(Material.id).where(Material.codigo == codigo))
    return result.scalar_one_or_none() is None


async def generar_codigo_unico(nombre: str, db: AsyncSession) -> str:
    base = generar_codigo_base(nombre)
    codigo = base
    sufijo = 2
    while not await _codigo_disponible(codigo, db):
        codigo = f"{base}-{sufijo}"
        sufijo += 1
    return codigo


async def crear_material(data: MaterialCreate, db: AsyncSession) -> Material:
    codigo = await generar_codigo_unico(data.nombre, db)
    material = Material(
        nombre=data.nombre,
        codigo=codigo,
        unidad=data.unidad,
        precio_actual=data.precio_actual,
    )
    db.add(material)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un material con ese nombre",
        )
    await db.refresh(material)
    return material


async def actualizar_material(material_id: int, data: MaterialPatch, db: AsyncSession) -> Material:
    if data.precio_actual is None and data.activo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar precio_actual y/o activo",
        )

    material = await get_material_or_404(material_id, db)
    if data.precio_actual is not None:
        material.precio_actual = data.precio_actual
    if data.activo is not None:
        material.activo = data.activo

    await db.commit()
    await db.refresh(material)
    return material
