from datetime import datetime

from pydantic import BaseModel


class HistorialPacaOut(BaseModel):
    id: int
    paca_id: int
    evento: str
    detalle_salida_id: int | None
    fecha: datetime
    usuario_id: int | None

    model_config = {"from_attributes": True}
