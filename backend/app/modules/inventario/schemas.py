from datetime import datetime

from pydantic import BaseModel


class InventarioOut(BaseModel):
    material_id: int
    peso_total: float
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class InventarioPacasOut(BaseModel):
    material_id: int
    cantidad: int
    actualizado_en: datetime

    model_config = {"from_attributes": True}
