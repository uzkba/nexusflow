from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config_auth import auth_settings
from backend.app.core.security import create_access_token, generate_refresh_token
from backend.app.db.session import get_db
from backend.app.schemas.auth_schema import LoginRequest, UsuarioOut
from backend.app.services.auth_service import autenticar_usuario, registrar_refresh_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UsuarioOut)
async def login(
    credenciais: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    usuario = await autenticar_usuario(db, credenciais.email, credenciais.senha)
    if usuario is None:
        # 401 genérico — não revela se o e-mail existe ou se foi a senha que errou
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    access_token = create_access_token(usuario.id, usuario.email, usuario.papel)
    refresh_token_puro = generate_refresh_token()
    await registrar_refresh_token(db, usuario.id, refresh_token_puro)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
        max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_puro,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/auth/refresh",
        max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    return usuario