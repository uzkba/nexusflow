"""
Testes de integração para /api/kpis, /api/graficos/potencia-uf e
/api/graficos/evolucao-anual.

Foco dos critérios de aceite:
  - projetos com status_revisao='pendente' DEVEM aparecer nos payloads;
  - projetos com cliente_id=NULL NÃO DEVEM aparecer nos payloads.

Usa as fixtures `client` e `db_session` do conftest.py (Postgres real via
testcontainers, asyncpg, transação com rollback por teste).
"""
import uuid
import pytest

from backend.app.enum import ReviewStatus
from backend.app.model.models import Client, GenerationProject

# Importações para simular o bypass de autenticação
from backend.main import app
from backend.app.core.auth_dependencies import get_current_user

_OUTRO_STATUS = next(s for s in ReviewStatus if s != ReviewStatus.pendente)


# Fixture automática para burlar a autenticação de TODAS as rotas neste arquivo
@pytest.fixture(autouse=True)
def bypass_autenticacao(usuario_ativo):
    app.dependency_overrides[get_current_user] = lambda: usuario_ativo
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _novo_ceg() -> str:
    return f"TEST-{uuid.uuid4().hex[:10].upper()}"


async def _seed(db_session):
    cliente_a_obj = Client(nome_oficial="Cliente Teste A")
    cliente_b_obj = Client(nome_oficial="Cliente Teste B")
    db_session.add_all([cliente_a_obj, cliente_b_obj])
    await db_session.flush()

    cliente_a = cliente_a_obj.id
    cliente_b = cliente_b_obj.id

    projetos = [
        GenerationProject(
            ceg=_novo_ceg(), cliente_id=cliente_a, uf="CE",
            potencia_outorgada_kw=10_000, inicio_vigencia_ano=2023,
            status_revisao=ReviewStatus.pendente,
        ),
        GenerationProject(
            ceg=_novo_ceg(), cliente_id=cliente_a, uf="CE",
            potencia_outorgada_kw=20_000, inicio_vigencia_ano=2024,
            status_revisao=_OUTRO_STATUS,
        ),
        GenerationProject(
            ceg=_novo_ceg(), cliente_id=cliente_b, uf="SP",
            potencia_outorgada_kw=30_000, inicio_vigencia_ano=2024,
            status_revisao=_OUTRO_STATUS,
        ),
        GenerationProject(
            ceg=_novo_ceg(), cliente_id=None, uf="SP",
            potencia_outorgada_kw=999_000, inicio_vigencia_ano=2024,
            status_revisao=_OUTRO_STATUS,
        ),
    ]
    db_session.add_all(projetos)
    await db_session.commit()


class TestKPIs:
    async def test_inclui_projetos_com_revisao_pendente(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/kpis")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_projetos"] == 3
        assert body["projetos_pendentes_revisao"] == 1

    async def test_exclui_projetos_sem_cliente_id(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/kpis")
        body = resp.json()
        assert float(body["potencia_total_mw"]) == 60.0


class TestPotenciaPorUF:
    async def test_agrega_por_uf_incluindo_pendentes(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/graficos/potencia-uf")
        assert resp.status_code == 200
        dados = {item["uf"]: item for item in resp.json()["dados"]}

        assert float(dados["CE"]["potencia_total"]) == 30.0
        assert dados["CE"]["total_projetos"] == 2

    async def test_nao_inclui_uf_de_projeto_sem_cliente(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/graficos/potencia-uf")
        dados = {item["uf"]: item for item in resp.json()["dados"]}
        assert float(dados["SP"]["potencia_total"]) == 30.0


class TestEvolucaoAnual:
    async def test_ordena_cronologicamente_e_inclui_pendentes(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/graficos/evolucao-anual")
        assert resp.status_code == 200
        dados = resp.json()["dados"]

        anos = [item["ano"] for item in dados]
        assert anos == sorted(anos)
        assert 2023 in anos

        por_ano = {item["ano"]: item for item in dados}
        assert float(por_ano[2023]["potencia_total"]) == 10.0

    async def test_potencia_acumulada_nao_soma_projeto_sem_cliente(self, client, db_session):
        await _seed(db_session)
        resp = await client.get("/api/graficos/evolucao-anual")
        dados = resp.json()["dados"]
        acumulado_final = dados[-1]["potencia_acumulada"]
        assert float(acumulado_final) == 60.0