from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UsuarioCreate(BaseModel):
    username: str
    password: str
    role: str = "revisor"   # admin | revisor | lectura


class UsuarioOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool


class ConfigValor(BaseModel):
    valor: str
