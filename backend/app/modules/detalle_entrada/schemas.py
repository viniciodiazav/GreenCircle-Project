from datetime import datetime

from pydantic import BaseModel, Field


class DetalleEntradaOut(BaseModel):
    id: int
    movimiento_id: int
    proveedor_id: int
    material_id: int
    peso_bruto: float
    tara: float
    peso_neto: float
    precio_compra: float
    fecha: datetime
    descripcion: str | None

    model_config = {"from_attributes": True}


class DetalleEntradaCreate(BaseModel):
    movimiento_id: int
    proveedor_id: int
    material_id: int
    peso_bruto: float = Field(gt=0)
    tara: float = Field(ge=0)
    descripcion: str | None = None
