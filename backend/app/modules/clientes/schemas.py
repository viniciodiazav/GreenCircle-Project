from pydantic import BaseModel


class ClienteOut(BaseModel):
    id: int
    nombre: str
    direccion: str | None
    contacto: str | None
    activo: bool

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    nombre: str
    direccion: str | None = None
    contacto: str | None = None


class ClientePatch(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    contacto: str | None = None
    activo: bool | None = None
