from typing import Literal

from pydantic import BaseModel, Field

Rol = Literal["operador", "administrador"]


class LoginRequest(BaseModel):
    usuario: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    id: int
    usuario: str
    activo: bool
    rol: Rol

    model_config = {"from_attributes": True}


class UsuarioCreate(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    rol: Rol = "operador"


class UsuarioPatch(BaseModel):
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    rol: Rol | None = None
