from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config_auth import auth_settings
from backend.app.core.security import verify_password, hash_refresh_token
from backend.app.model.models import User, RefreshToken


async def autenticar_usuario(db: AsyncSession, email: str, senha: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    usuario = result.scalar_one_or_none()

    if usuario is None or not usuario.ativo:
        return None
    if not verify_password(senha, usuario.senha_hash):
        return None

    return usuario


async def registrar_refresh_token(db: AsyncSession, usuario_id, token_puro: str) -> RefreshToken:
    novo_token = RefreshToken(
        usuario_id=usuario_id,
        token_hash=hash_refresh_token(token_puro),
        expira_em=datetime.now(timezone.utc) + timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(novo_token)
    await db.commit()
    await db.refresh(novo_token)
    return novo_token