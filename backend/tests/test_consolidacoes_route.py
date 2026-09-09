"""
Testes de integração de /api/consolidacoes.

Seguem o padrão da suíte de auth: PostgreSQL real via testcontainers,
isolamento por transação/rollback por teste, e httpx.AsyncClient com ASGITransport.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt

from backend.app.enum import ConsolidationStatus, UserRole
from backend.app.enum.consolidacao import MotivoPendenciaEnum
from backend.app.model.models import PendingConsolidation, User, Client

pytestmark = pytest.mark.asyncio

ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

async def _criar_usuario(db_session) -> User:
    usuario = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4()}@nexusflow.test",
        senha_hash="hash-nao-usado-neste-teste",
        papel=UserRole.admin,
        ativo=True,
    )
    db_session.add(usuario)
    await db_session.flush()  # Substituído commit() por flush() para não quebrar o rollback do teste
    await db_session.refresh(usuario)
    return usuario

async def _criar_cliente(db_session):
    cliente = Client(id=uuid.uuid4(), nome="Cliente Teste")
    db_session.add(cliente)
    await db_session.flush()
    return cliente.id

def _gerar_token(usuario: User) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "papel": usuario.papel.value,
        "iat": agora,
        "exp": agora + timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
    }
    # Adicionado fallback para evitar erro se a var de ambiente não estiver setada no teste
    secret = os.environ.get("JWT_SECRET_KEY", "secret-test-key")
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


async def _client_autenticado(client: AsyncClient, usuario: User) -> AsyncClient:
    token = _gerar_token(usuario)
    client.cookies.set("access_token", token)
    return client


async def _criar_pendencia_consolidacao_nome(
    db_session, status: ConsolidationStatus = ConsolidationStatus.pendente
) -> PendingConsolidation:
    item = PendingConsolidation(
        motivo_pendencia=MotivoPendenciaEnum.consolidacao_nome,
        status=status,
        nome_bruto_id=None,
        cliente_sugerido_id=None,  # <-- CORREÇÃO AQUI: removido uuid.uuid4() para evitar erro de FK
        score_similaridade=92.5,
        ceg=None,
        diff_pendente=None,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


async def _criar_pendencia_alteracao_dado(
    db_session,
    ceg: str | None = None, # <-- CORREÇÃO AQUI: Passando None por padrão para evitar erro de FK
    status: ConsolidationStatus = ConsolidationStatus.pendente,
) -> PendingConsolidation:
    item = PendingConsolidation(
        motivo_pendencia=MotivoPendenciaEnum.alteracao_dado,
        status=status,
        nome_bruto_id=None,
        cliente_sugerido_id=None,
        score_similaridade=None,
        ceg=ceg,
        diff_pendente={"potencia_outorgada_kw": {"de": 100.0, "para": 120.0}},
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# GET /api/consolidacoes/pendentes
# ---------------------------------------------------------------------------

class TestListarPendentes:
    async def test_retorna_apenas_status_pendente(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)

        pendente = await _criar_pendencia_consolidacao_nome(db_session)
        await _criar_pendencia_consolidacao_nome(
            db_session, status=ConsolidationStatus.aprovado
        )

        response = await client.get("/api/consolidacoes/pendentes")

        assert response.status_code == 200
        ids = [item["id"] for item in response.json()]
        
        # CORREÇÃO AQUI: removido o str()
        assert ids == [pendente.id]

    async def test_inclui_motivo_pendencia_dos_dois_tipos(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)

        await _criar_pendencia_consolidacao_nome(db_session)
        await _criar_pendencia_alteracao_dado(db_session)

        response = await client.get("/api/consolidacoes/pendentes")

        motivos = {item["motivo_pendencia"] for item in response.json()}
        assert motivos == {
            MotivoPendenciaEnum.consolidacao_nome.value,
            MotivoPendenciaEnum.alteracao_dado.value,
        }

    async def test_sem_autenticacao_retorna_401(self, client: AsyncClient):
        response = await client.get("/api/consolidacoes/pendentes")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/consolidacoes/{id}/aprovar
# ---------------------------------------------------------------------------

class TestAprovar:
    async def test_consolidacao_nome_mantem_diff_pendente_nulo(
        self, client: AsyncClient, db_session
    ):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)
        item = await _criar_pendencia_consolidacao_nome(db_session)

        response = await client.patch(f"/api/consolidacoes/{item.id}/aprovar")

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["status"] == ConsolidationStatus.aprovado.value
        assert corpo["diff_pendente"] is None

    async def test_alteracao_dado_limpa_diff_pendente(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)
        item = await _criar_pendencia_alteracao_dado(db_session)
        assert item.diff_pendente is not None  # pré-condição

        response = await client.patch(f"/api/consolidacoes/{item.id}/aprovar")

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["status"] == ConsolidationStatus.aprovado.value
        assert corpo["diff_pendente"] is None

    async def test_registra_decidido_por_e_decidido_em(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)
        item = await _criar_pendencia_consolidacao_nome(db_session)

        antes = datetime.now(timezone.utc) - timedelta(seconds=5)
        response = await client.patch(f"/api/consolidacoes/{item.id}/aprovar")
        corpo = response.json()

        assert corpo["decidido_por"] == str(usuario.id)
        decidido_em = datetime.fromisoformat(corpo["decidido_em"])
        assert decidido_em >= antes

    async def test_pendencia_ja_decidida_retorna_409(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)
        item = await _criar_pendencia_consolidacao_nome(
            db_session, status=ConsolidationStatus.aprovado
        )

        response = await client.patch(f"/api/consolidacoes/{item.id}/aprovar")

        assert response.status_code == 409

    async def test_id_inexistente_retorna_404(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)

        # Retornado para Integer. O FastAPI vai validar como tipo correto,
        # buscar no banco, não encontrar e aí sim retornar 404.
        response = await client.patch("/api/consolidacoes/999999/aprovar")

        assert response.status_code == 404

    async def test_sem_autenticacao_retorna_401(self, client: AsyncClient, db_session):
        item = await _criar_pendencia_consolidacao_nome(db_session)

        response = await client.patch(f"/api/consolidacoes/{item.id}/aprovar")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/consolidacoes/{id}/rejeitar
# ---------------------------------------------------------------------------

class TestRejeitar:
    async def test_preserva_diff_pendente_para_auditoria(self, client: AsyncClient, db_session):
        usuario = await _criar_usuario(db_session)
        await _client_autenticado(client, usuario)
        item = await _criar_pendencia_alteracao_dado(db_session)

        response = await client.patch(f"/api/consolidacoes/{item.id}/rejeitar")

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["status"] == ConsolidationStatus.rejeitado.value
        assert corpo["diff_pendente"] is not None

    async def test_sem_autenticacao_retorna_401(self, client: AsyncClient, db_session):
        item = await _criar_pendencia_consolidacao_nome(db_session)

        response = await client.patch(f"/api/consolidacoes/{item.id}/rejeitar")

        assert response.status_code == 401