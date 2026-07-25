from datetime import datetime

from pydantic import BaseModel, Field


class PacaOut(BaseModel):
    id: int
    codigo: str
    material_id: int
    peso: float
    en_inventario: bool
    fecha_registro: datetime
    detalle_salida_id: int | None

    model_config = {"from_attributes": True}


class PacaCreate(BaseModel):
    material_id: int
    peso: float = Field(gt=0)
