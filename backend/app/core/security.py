import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext

from backend.app.core.config_auth import auth_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(senha: str) -> str:
    return pwd_context.hash(senha)


def verify_password(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def create_access_token(usuario_id, email: str, papel: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "papel": papel,
        "iat": now,
        "exp": now + timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, auth_settings.SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def decode_access_token(token: str) -> dict:
    """
    Decodifica e valida o access token JWT.
    Lança jose.JWTError se assinatura ou exp forem inválidos.
    """
    return jwt.decode(
        token,
        auth_settings.SECRET_KEY,
        algorithms=[auth_settings.JWT_ALGORITHM],
    )