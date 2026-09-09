# tests/integration/test_auth_dependencies.py

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import AsyncClient, ASGITransport
from jose import jwt

from backend.app.core.config_auth import auth_settings
from backend.app.core.security import create_access_token
from backend.app.core.auth_dependencies import get_current_user, require_admin


# --- App de teste isolado, só com uma rota protegida fake ---
# main.py ainda não tem nenhuma rota protegida real (só auth_route),
# então testamos a dependency isolada, sem acoplar a rotas de negócio
# que ainda não existem. Não depende de banco, por isso não usa
# db_session/postgres_container — só usuario_ativo, para ter um id/email
# reais no token.

def build_middleware_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protegida")
    async def rota_protegida(user: dict = Depends(get_current_user)):
        return {"sub": user["sub"], "papel": user["papel"]}

    @app.get("/apenas-admin")
    async def rota_admin(user: dict = Depends(require_admin)):
        return {"sub": user["sub"]}

    return app


@pytest_asyncio.fixture()
async def middleware_client():
    app = build_middleware_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Helpers para gerar tokens não-padrão (expirado, assinatura errada, etc.) ---

def _token_expirado(usuario_id, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "papel": "admin",
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),  # já expirado
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, auth_settings.SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM)


def _token_assinatura_invalida(usuario_id, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "papel": "admin",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid4()),
    }
    # assinado com uma chave diferente da usada pela aplicação
    return jwt.encode(payload, "chave-secreta-errada", algorithm=auth_settings.JWT_ALGORITHM)


def _token_sem_claims_obrigatorias() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iat": now,
        "exp": now + timedelta(minutes=15),
        # "sub" e "papel" propositalmente ausentes
    }
    return jwt.encode(payload, auth_settings.SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM)


# --- Testes ---

@pytest.mark.asyncio
async def test_sem_cookie_retorna_401(middleware_client: AsyncClient):
    response = await middleware_client.get("/protegida")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_expirado_retorna_401(middleware_client: AsyncClient, usuario_ativo):
    token = _token_expirado(usuario_ativo.id, usuario_ativo.email)
    middleware_client.cookies.set("access_token", token)
    response = await middleware_client.get("/protegida")
    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado"


@pytest.mark.asyncio
async def test_assinatura_invalida_retorna_401(middleware_client: AsyncClient, usuario_ativo):
    token = _token_assinatura_invalida(usuario_ativo.id, usuario_ativo.email)
    middleware_client.cookies.set("access_token", token)
    response = await middleware_client.get("/protegida")
    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado"


@pytest.mark.asyncio
async def test_token_malformado_sem_claims_retorna_401(middleware_client: AsyncClient):
    token = _token_sem_claims_obrigatorias()
    middleware_client.cookies.set("access_token", token)
    response = await middleware_client.get("/protegida")
    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"


@pytest.mark.asyncio
async def test_token_valido_permite_acesso_e_injeta_payload(middleware_client: AsyncClient, usuario_ativo):
    token = create_access_token(usuario_ativo.id, usuario_ativo.email, usuario_ativo.papel)
    middleware_client.cookies.set("access_token", token)
    response = await middleware_client.get("/protegida")
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == str(usuario_ativo.id)
    assert body["papel"] == "admin"


@pytest.mark.asyncio
async def test_token_valido_com_papel_admin_acessa_rota_admin(middleware_client: AsyncClient, usuario_ativo):
    token = create_access_token(usuario_ativo.id, usuario_ativo.email, usuario_ativo.papel)
    middleware_client.cookies.set("access_token", token)
    response = await middleware_client.get("/apenas-admin")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cookie_vazio_string_retorna_401(middleware_client: AsyncClient):
    middleware_client.cookies.set("access_token", "")
    response = await middleware_client.get("/protegida")
    assert response.status_code == 401