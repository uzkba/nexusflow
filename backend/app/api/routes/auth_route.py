from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config_auth import auth_settings
from backend.app.core.security import create_access_token, generate_refresh_token
from backend.app.db.session import get_db
# 🔍 Importação atualizada com os novos schemas
from backend.app.schemas.auth_schema import (
    LoginRequest, 
    UsuarioOut, 
    LoginResponse, 
    RefreshRequest, 
    RefreshResponse
)
from backend.app.services.auth_service import autenticar_usuario, registrar_refresh_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

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
    
    # Mantém os cookies caso decida usá-los no futuro
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE,
        path="/", max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token_puro, httponly=True,
        secure=auth_settings.COOKIE_SECURE, samesite=auth_settings.COOKIE_SAMESITE,
        path="/api/auth/refresh", max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    
    # RETORNA NO JSON PARA O FRONTEND (AuthContext.tsx) LER!
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_puro,
        "user": usuario
    }

@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    # Aqui você precisará de uma função no seu auth_service para validar se o 
    # refresh_token enviado ainda é válido e pertence a um usuário.
    # Exemplo:
    # usuario = await validar_refresh_token(db, req.refresh_token)
    # if not usuario:
    #     raise HTTPException(status_code=401, detail="Refresh token inválido")
    
    # Para destravar temporariamente (mock), ou se já tiver a função, substitua:
    novo_access_token = "novo_token_gerado" # Substitua pela chamada real
    novo_refresh_token = "novo_refresh_gerado" # Substitua pela chamada real
    
    return {
        "access_token": novo_access_token,
        "refresh_token": novo_refresh_token
    }