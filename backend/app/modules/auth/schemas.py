from pydantic import BaseModel


class LoginRequest(BaseModel):
    usuario: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
