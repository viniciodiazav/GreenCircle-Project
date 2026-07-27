from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}


class UsuarioCreate(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)


class UsuarioPatch(BaseModel):
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8)
