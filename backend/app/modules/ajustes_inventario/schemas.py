from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AjusteInventarioOut(BaseModel):
    id: int
    material_id: int
    peso_ajuste: float
    motivo: str
    comentarios: str | None
    fecha: datetime
    creado_por: int | None

    model_config = {"from_attributes": True}


class AjusteInventarioCreate(BaseModel):
    material_id: int
    peso_ajuste: float
    motivo: str = Field(min_length=1)
    comentarios: str | None = None

    @field_validator("peso_ajuste")
    @classmethod
    def peso_ajuste_no_puede_ser_cero(cls, valor: float) -> float:
        if valor == 0:
            raise ValueError("peso_ajuste no puede ser 0")
        return valor
