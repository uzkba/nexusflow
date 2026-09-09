"""
Testes do endpoint POST /api/auth/login.
Cobre os critérios de aceite da issue: credenciais válidas (200 +
tokens), credenciais inválidas (401) e, por extensão do doc de
modelagem, usuário inativo (401 genérico, sem vazar o motivo).
"""
import hashlib

from sqlalchemy import select

from backend.app.model.models import RefreshToken


async def test_login_sucesso_retorna_200_e_dados_do_usuario(client, usuario_ativo):
    response = await client.post(
        "/api/auth/login",
        json={"email": usuario_ativo.email, "senha": "senha-correta-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == usuario_ativo.email
    assert body["papel"] == "admin"
    assert "senha" not in body
    assert "senha_hash" not in body
    assert "token" not in str(body).lower()  # tokens não vão no corpo


async def test_login_sucesso_define_cookies_httponly(client, usuario_ativo):
    response = await client.post(
        "/api/auth/login",
        json={"email": usuario_ativo.email, "senha": "senha-correta-123"},
    )

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert len(set_cookie_headers) == 2

    access_cookie = next(h for h in set_cookie_headers if h.startswith("access_token="))
    refresh_cookie = next(h for h in set_cookie_headers if h.startswith("refresh_token="))

    assert "HttpOnly" in access_cookie
    assert "SameSite=strict" in access_cookie.lower().replace("samesite=strict", "SameSite=strict") or "samesite=strict" in access_cookie.lower()
    assert "Path=/" in access_cookie

    assert "HttpOnly" in refresh_cookie
    assert "Path=/api/auth/refresh" in refresh_cookie


async def test_login_grava_hash_do_refresh_token_no_banco(client, db_session, usuario_ativo):
    response = await client.post(
        "/api/auth/login",
        json={"email": usuario_ativo.email, "senha": "senha-correta-123"},
    )

    # extrai o valor puro do cookie pra confirmar que só o hash foi persistido
    refresh_cookie_header = next(
        h for h in response.headers.get_list("set-cookie") if h.startswith("refresh_token=")
    )
    token_puro = refresh_cookie_header.split("refresh_token=")[1].split(";")[0]
    hash_esperado = hashlib.sha256(token_puro.encode()).hexdigest()

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.usuario_id == usuario_ativo.id)
    )
    registro = result.scalar_one()

    assert registro.token_hash == hash_esperado
    assert registro.revogado_em is None
    assert registro.expira_em is not None


async def test_login_senha_incorreta_retorna_401_generico(client, usuario_ativo):
    response = await client.post(
        "/api/auth/login",
        json={"email": usuario_ativo.email, "senha": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"
    assert "set-cookie" not in response.headers


async def test_login_email_inexistente_retorna_401_generico(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nao-existe@painel.com", "senha": "qualquer-coisa"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


async def test_login_usuario_inativo_retorna_401(client, usuario_inativo):
    response = await client.post(
        "/api/auth/login",
        json={"email": usuario_inativo.email, "senha": "senha-correta-123"},
    )

    # mesmo 401 genérico do caso de senha errada — não revela que o
    # e-mail existe mas está desativado (ver Seção 5.1 do doc de auth)
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


async def test_login_email_invalido_retorna_422(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nao-e-email", "senha": "qualquer-coisa"},
    )

    assert response.status_code == 422