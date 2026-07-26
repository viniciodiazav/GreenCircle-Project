from datetime import datetime

from pydantic import BaseModel


class TicketVentaOut(BaseModel):
    id: int
    movimiento_id: int
    folio: str
    cliente: str
    cantidad_pacas: int
    materiales: list[str]
    fecha: datetime

    model_config = {"from_attributes": True}
