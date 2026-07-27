from datetime import datetime

from pydantic import BaseModel, Field


class DetalleEntradaOut(BaseModel):
    id: int
    movimiento_id: int
    proveedor_id: int
    material_id: int
    peso_bruto: float
    tara: float
    descuento: float
    peso_neto: float
    precio_compra: float
    monto_total: float
    fecha: datetime
    descripcion: str | None
    descripcion_descuento: str | None
    creado_por: int | None

    model_config = {"from_attributes": True}


class DetalleEntradaCreate(BaseModel):
    movimiento_id: int
    proveedor_id: int
    material_id: int
    peso_bruto: float = Field(gt=0)
    tara: float = Field(ge=0)
    descuento: float = Field(default=0, ge=0, le=100)
    monto_total: float = Field(ge=0)
    descripcion: str | None = None
    descripcion_descuento: str | None = None


class DetalleEntradaPatch(BaseModel):
    """Corrige una línea mal capturada -- solo mientras el movimiento sigue
    abierto. proveedor_id/material_id/movimiento_id NO son editables: si
    esos están mal, se cancela la línea (DELETE) y se crea una nueva."""

    peso_bruto: float | None = Field(default=None, gt=0)
    tara: float | None = Field(default=None, ge=0)
    descuento: float | None = Field(default=None, ge=0, le=100)
    monto_total: float | None = Field(default=None, ge=0)
    descripcion: str | None = None
    descripcion_descuento: str | None = None
