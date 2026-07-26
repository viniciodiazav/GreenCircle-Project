from datetime import datetime

from pydantic import BaseModel


class TicketCompraOut(BaseModel):
    id: int
    movimiento_id: int
    folio: str
    proveedor: str
    materiales: list[str]
    fecha: datetime

    model_config = {"from_attributes": True}
