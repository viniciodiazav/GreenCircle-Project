from datetime import datetime

from pydantic import BaseModel, Field


class DetalleSalidaOut(BaseModel):
    id: int
    movimiento_id: int
    cliente_id: int
    precio_venta: float
    monto_total: float
    fecha: datetime
    descripcion: str | None
    cantidad_pacas: int
    creado_por: int | None

    model_config = {"from_attributes": True}


class DetalleSalidaCreate(BaseModel):
    movimiento_id: int
    cliente_id: int
    precio_venta: float = Field(gt=0)
    monto_total: float = Field(ge=0)
    pacas: list[int] = Field(min_length=1, description="ids de las pacas que se venden")
    descripcion: str | None = None


class DetalleSalidaPatch(BaseModel):
    """Corrige una línea mal capturada -- solo mientras el movimiento sigue
    abierto. cliente_id/pacas NO son editables: si el cliente está mal o
    hay que cambiar qué pacas se vendieron, se cancela la línea (DELETE,
    libera las pacas) y se crea una nueva."""

    precio_venta: float | None = Field(default=None, gt=0)
    monto_total: float | None = Field(default=None, ge=0)
    descripcion: str | None = None
