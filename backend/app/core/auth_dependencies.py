from fastapi import Request, Depends, HTTPException, status
from jose import JWTError

from backend.app.core.security import decode_access_token


COOKIE_NAME = "access_token"


async def get_current_user(request: Request) -> dict:
    """
    Dependency de autenticação. Lê o access token do cookie HttpOnly,
    valida assinatura e expiração, injeta o payload no contexto da rota.

    401 -> token ausente, malformado, expirado ou assinatura inválida
    403 -> reservado para autorização por papel (ver require_admin)
    """
    token = request.cookies.get(COOKIE_NAME)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    if "sub" not in payload or "papel" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    return payload


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Autorização por papel — hoje redundante (só existe 'admin'),
    mas deixa pronto para um 2º papel futuro sem tocar nas rotas.
    """
    if user.get("papel") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )
    return user