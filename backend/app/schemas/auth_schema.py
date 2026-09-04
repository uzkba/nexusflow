from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    id: UUID
    email: EmailStr
    papel: str

    model_config = ConfigDict(from_attributes=True)