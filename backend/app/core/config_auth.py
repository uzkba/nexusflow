"""
Configuração de autenticação: segredo de assinatura JWT e parâmetros
de expiração de token. Falha rápido na importação, mesmo padrão de
config_infra.py — só que aqui é config de auth, não infra de processo.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _obter_secret_key() -> str:
    valor = os.getenv("JWT_SECRET_KEY")
    if not valor:
        raise RuntimeError(
            "JWT_SECRET_KEY nao definida. Confira o .env (copiado do "
            ".env.example)."
        )
    return valor


class AuthSettings:
    SECRET_KEY: str = _obter_secret_key()
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


auth_settings = AuthSettings()