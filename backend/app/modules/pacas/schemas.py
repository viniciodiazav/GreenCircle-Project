from datetime import datetime

from pydantic import BaseModel


class PacaOut(BaseModel):
    id: int
    codigo: str
    material_id: int
    en_inventario: bool
    fecha_registro: datetime
    detalle_salida_id: int | None

    model_config = {"from_attributes": True}


class PacaCreate(BaseModel):
    codigo: str
    material_id: int
