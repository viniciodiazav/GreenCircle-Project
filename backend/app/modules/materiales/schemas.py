from datetime import datetime

from pydantic import BaseModel, Field


class MaterialOut(BaseModel):
    id: int
    nombre: str
    codigo: str
    unidad: str
    precio_actual: float
    activo: bool
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class MaterialPublicOut(BaseModel):
    nombre: str
    precio: float


class MaterialCreate(BaseModel):
    nombre: str
    unidad: str = "kg"
    precio_actual: float = Field(gt=0)


class MaterialPatch(BaseModel):
    precio_actual: float | None = Field(default=None, gt=0)
    activo: bool | None = None
