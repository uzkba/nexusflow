"""
Testes de integração do endpoint GET /api/projetos.

Pressupõe que o projeto já tenha (da fase de setup de testes):
  - fixture `client`      -> httpx.AsyncClient (ou AsyncClient do FastAPI),
                              com o banco de testes limpo
  - fixture `db_session`  -> AsyncSession do SQLAlchemy apontando pro
                              mesmo banco de testes

Se os nomes das fixtures no seu conftest.py forem diferentes, ajuste os
parâmetros das funções abaixo (ou o import de `app.models.projeto`).

Requer pytest-asyncio. Se seu projeto não usa `asyncio_mode = auto` no
pytest.ini/pyproject.toml, o marcador `pytestmark` abaixo já cobre todo
o módulo.
"""

import itertools

import pytest

from backend.app.model import GenerationProject

pytestmark = pytest.mark.asyncio

_ceg_seq = itertools.count(1)


def _criar_projeto(db_session, **kwargs):
    """Helper para popular o banco de testes com valores default sensatos,
    sobrescrevendo apenas o que cada teste precisar variar.

    `ceg` é a PK (string) do model — se não for passado, gera um valor
    único incremental para não colidir entre projetos do mesmo teste.
    Apenas monta e adiciona o objeto à sessão; o commit é feito pelo
    chamador (await), já que `db_session` aqui é assíncrona.
    """
    defaults = {
        "ceg": f"UFV.PE.PB.{next(_ceg_seq):06d}",
        "nome_projeto": "Projeto Teste",
        "uf": "PB",
        "origem": "SIGA",
        "fase": "Operação",
        "potencia_outorgada_kw": 1000.0,
    }
    defaults.update(kwargs)
    projeto = GenerationProject(**defaults)
    db_session.add(projeto)
    return projeto


@pytest.fixture
async def seed_25_projetos(db_session):
    """25 projetos numerados, para exercitar a paginação (size padrão = 20)."""
    for i in range(1, 26):
        _criar_projeto(
            db_session,
            nome_projeto=f"Projeto {i:02d}",
            uf="PB" if i % 2 == 0 else "SP",
            fase="Operação" if i % 3 != 0 else "Construção",
        )
    await db_session.commit()


class TestPaginacao:
    async def test_primeira_pagina_usa_tamanho_padrao(self, client, seed_25_projetos):
        resp = await client.get("/api/projetos")
        assert resp.status_code == 200

        body = resp.json()
        assert body["total"] == 25
        assert body["page"] == 1
        assert body["size"] == 20
        assert body["pages"] == 2
        assert len(body["items"]) == 20

    async def test_segunda_pagina_retorna_os_itens_restantes(
        self, client, seed_25_projetos
    ):
        resp = await client.get("/api/projetos", params={"page": 2, "size": 20})
        assert resp.status_code == 200

        body = resp.json()
        assert body["page"] == 2
        assert body["total"] == 25
        # 25 itens, size 20 -> segunda página deve ter só os 5 restantes
        assert len(body["items"]) == 5

        # e não deve repetir nenhum item já visto na primeira página
        resp_pagina_1 = await client.get(
            "/api/projetos", params={"page": 1, "size": 20}
        )
        cegs_pagina_1 = {item["ceg"] for item in resp_pagina_1.json()["items"]}
        cegs_pagina_2 = {item["ceg"] for item in body["items"]}
        assert cegs_pagina_1.isdisjoint(cegs_pagina_2)

    async def test_size_customizado(self, client, seed_25_projetos):
        resp = await client.get("/api/projetos", params={"page": 3, "size": 10})
        body = resp.json()

        assert body["pages"] == 3  # ceil(25/10)
        assert len(body["items"]) == 5  # última página, sobra de 5

    async def test_pagina_alem_do_total_retorna_lista_vazia(
        self, client, seed_25_projetos
    ):
        resp = await client.get("/api/projetos", params={"page": 99, "size": 20})
        body = resp.json()

        assert resp.status_code == 200
        assert body["total"] == 25
        assert body["items"] == []


class TestFiltros:
    async def test_filtro_unico_por_uf(self, client, db_session):
        _criar_projeto(db_session, nome_projeto="Solar PB 1", uf="PB")
        _criar_projeto(db_session, nome_projeto="Solar PB 2", uf="PB")
        _criar_projeto(db_session, nome_projeto="Solar SP 1", uf="SP")
        await db_session.commit()

        resp = await client.get("/api/projetos", params={"uf": "PB"})
        body = resp.json()

        assert resp.status_code == 200
        assert body["total"] == 2
        assert all(item["uf"] == "PB" for item in body["items"])

    async def test_filtro_status_mapeia_para_coluna_fase(self, client, db_session):
        _criar_projeto(db_session, nome_projeto="Em operação", fase="Operação")
        _criar_projeto(db_session, nome_projeto="Em construção", fase="Construção")
        await db_session.commit()

        resp = await client.get("/api/projetos", params={"status": "Operação"})
        body = resp.json()

        assert body["total"] == 1
        assert body["items"][0]["fase"] == "Operação"

    async def test_filtro_search_busca_parcial_case_insensitive(
        self, client, db_session
    ):
        _criar_projeto(db_session, nome_projeto="Fazenda Solar Cariri")
        _criar_projeto(db_session, nome_projeto="Parque Eólico Borborema")
        await db_session.commit()

        resp = await client.get("/api/projetos", params={"search": "solar"})
        body = resp.json()

        assert body["total"] == 1
        assert "Cariri" in body["items"][0]["nome_projeto"]

    async def test_multiplos_filtros_simultaneos(self, client, db_session):
        _criar_projeto(
            db_session, nome_projeto="A", uf="PB", fase="Operação", origem="SIGA"
        )
        _criar_projeto(
            db_session, nome_projeto="B", uf="PB", fase="Construção", origem="SIGA"
        )
        _criar_projeto(
            db_session, nome_projeto="C", uf="SP", fase="Operação", origem="SIGA"
        )
        _criar_projeto(
            db_session, nome_projeto="D", uf="PB", fase="Operação", origem="Manual"
        )
        await db_session.commit()

        resp = await client.get(
            "/api/projetos",
            params={"uf": "PB", "status": "Operação", "origem": "SIGA"},
        )
        body = resp.json()

        assert resp.status_code == 200
        assert body["total"] == 1
        assert body["items"][0]["nome_projeto"] == "A"

    async def test_filtros_combinados_com_paginacao(self, client, db_session):
        for i in range(1, 16):
            _criar_projeto(
                db_session, nome_projeto=f"PB {i:02d}", uf="PB", fase="Operação"
            )
        for i in range(1, 6):
            _criar_projeto(
                db_session, nome_projeto=f"SP {i:02d}", uf="SP", fase="Operação"
            )
        await db_session.commit()

        resp = await client.get(
            "/api/projetos", params={"uf": "PB", "page": 2, "size": 10}
        )
        body = resp.json()

        assert body["total"] == 15  # total filtrado, não o total geral (20)
        assert body["pages"] == 2
        assert len(body["items"]) == 5
        assert all(item["uf"] == "PB" for item in body["items"])

    async def test_filtro_sem_resultados_retorna_total_zero(self, client, db_session):
        _criar_projeto(db_session, uf="PB")
        await db_session.commit()

        resp = await client.get("/api/projetos", params={"uf": "RR"})
        body = resp.json()

        assert body["total"] == 0
        assert body["items"] == []
        assert body["pages"] == 0