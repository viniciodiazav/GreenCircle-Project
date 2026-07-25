from datetime import datetime

from pydantic import BaseModel, Field


class DetalleSalidaOut(BaseModel):
    id: int
    movimiento_id: int
    cliente_id: int
    precio_venta: float
    fecha: datetime
    descripcion: str | None
    cantidad_pacas: int

    model_config = {"from_attributes": True}


class DetalleSalidaCreate(BaseModel):
    movimiento_id: int
    cliente_id: int
    precio_venta: float = Field(gt=0)
    pacas: list[int] = Field(min_length=1, description="ids de las pacas que se venden")
    descripcion: str | None = None
