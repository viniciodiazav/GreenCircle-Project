from datetime import datetime

from pydantic import BaseModel


class HistorialPrecioOut(BaseModel):
    id: int
    material_id: int
    precio_anterior: float
    precio_nuevo: float
    fecha_cambio: datetime

    model_config = {"from_attributes": True}
