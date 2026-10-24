from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config_auth import auth_settings
from backend.app.core.security import create_access_token, generate_refresh_token
from backend.app.db.session import get_db
from backend.app.schemas.auth_schema import LoginRequest, LoginResponse
from backend.app.services.auth_service import (
    autenticar_usuario, 
    registrar_refresh_token,
    validar_e_rotacionar_refresh_token,
    revogar_refresh_token
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE,
        path="/", max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE,
        path="/api/auth/refresh", max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

def _clear_auth_cookies(response: Response):
    response.delete_cookie(key="access_token", path="/", secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE)
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh", secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE)


@router.post("/login", response_model=LoginResponse)
async def login(
    credenciais: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    usuario = await autenticar_usuario(db, credenciais.email, credenciais.senha)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
        
    access_token = create_access_token(usuario.id, usuario.email, usuario.papel)
    refresh_token_puro = generate_refresh_token()
    await registrar_refresh_token(db, usuario.id, refresh_token_puro)
    
    _set_auth_cookies(response, access_token, refresh_token_puro)
    
    return {"user": usuario}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    token_puro = request.cookies.get("refresh_token")
    if not token_puro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")

    usuario = await validar_e_rotacionar_refresh_token(db, token_puro)
    if not usuario:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada")

    novo_access_token = create_access_token(usuario.id, usuario.email, usuario.papel)
    novo_refresh_token_puro = generate_refresh_token()
    await registrar_refresh_token(db, usuario.id, novo_refresh_token_puro)

    _set_auth_cookies(response, novo_access_token, novo_refresh_token_puro)
    return {"detail": "Sessão renovada"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    token_puro = request.cookies.get("refresh_token")
    if token_puro:
        await revogar_refresh_token(db, token_puro)
    
    _clear_auth_cookies(response)
    return {"detail": "Logout realizado com sucesso"}