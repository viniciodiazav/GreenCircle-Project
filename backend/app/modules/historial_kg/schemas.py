from datetime import datetime

from pydantic import BaseModel


class HistorialKgOut(BaseModel):
    id: int
    material_id: int
    peso_anterior: float
    peso_nuevo: float
    fecha_cambio: datetime
    usuario_id: int | None

    model_config = {"from_attributes": True}
