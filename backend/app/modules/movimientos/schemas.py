from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MovimientoOut(BaseModel):
    id: int
    tipo: str
    fecha: datetime
    cerrado: bool
    descripcion: str | None

    model_config = {"from_attributes": True}


class MovimientoCreate(BaseModel):
    tipo: Literal["ENTRADA", "SALIDA"]
    descripcion: str | None = None


class MovimientoPatch(BaseModel):
    descripcion: str | None = None
