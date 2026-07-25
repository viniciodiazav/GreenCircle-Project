from datetime import datetime

from pydantic import BaseModel


class HistorialPacaOut(BaseModel):
    id: int
    paca_id: int
    evento: str
    detalle_salida_id: int | None
    fecha: datetime

    model_config = {"from_attributes": True}
