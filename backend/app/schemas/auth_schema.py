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


class LoginResponse(BaseModel):
    # Tokens removidos: eles agora vão via Set-Cookie no header da resposta
    user: UsuarioOut


# RefreshRequest foi deletado. O backend vai ler o token direto do objeto Request (cookies)

class RefreshResponse(BaseModel):
    # Tokens removidos: a renovação injeta novos cookies diretamente
    detail: str