"""
Testes de integração do endpoint GET /api/geolocalizacao.

Assume fixtures `db_session` (AsyncSession de teste) e `client`
(httpx.AsyncClient) já existentes no conftest.py do projeto, seguindo o
padrão pytest-asyncio usado nos demais testes de integração do NexusFlow.
"""
import pytest

from backend.app.model import GenerationProject

pytestmark = pytest.mark.asyncio


async def test_geolocalizacao_agrega_quantidade_e_potencia(db_session, client):
    db_session.add_all(
        [
            GenerationProject(
                ceg="CEG-001",
                uf="SP",
                municipios=["Campinas"],
                potencia_outorgada_kw=100,
            ),
            GenerationProject(
                ceg="CEG-002",
                uf="SP",
                municipios=["Campinas"],
                potencia_outorgada_kw=50,
            ),
            GenerationProject(
                ceg="CEG-003",
                uf="BA",
                municipios=["Salvador"],
                potencia_outorgada_kw=200,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/geolocalizacao")
    assert response.status_code == 200

    data = response.json()
    campinas = next(d for d in data["dados"] if d["municipio"] == "Campinas")
    salvador = next(d for d in data["dados"] if d["municipio"] == "Salvador")

    assert campinas["uf"] == "SP"
    assert campinas["quantidade_projetos"] == 2
    assert campinas["potencia_total"] == 150.0

    assert salvador["quantidade_projetos"] == 1
    assert salvador["potencia_total"] == 200.0


async def test_geolocalizacao_projeto_com_multiplos_municipios_conta_em_cada_um(
    db_session, client
):
    db_session.add(
        GenerationProject(
            ceg="CEG-010",
            uf="MG",
            municipios=["Uberlândia", "Araguari"],
            potencia_outorgada_kw=300,
        )
    )
    await db_session.commit()

    response = await client.get("/api/geolocalizacao")
    data = response.json()

    ub = next(d for d in data["dados"] if d["municipio"] == "Uberlândia")
    ar = next(d for d in data["dados"] if d["municipio"] == "Araguari")

    # o mesmo projeto é contabilizado em cada município ao qual pertence
    assert ub["quantidade_projetos"] == 1
    assert ub["potencia_total"] == 300.0
    assert ar["quantidade_projetos"] == 1
    assert ar["potencia_total"] == 300.0


async def test_geolocalizacao_ignora_registros_com_localizacao_nula(
    db_session, client
):
    db_session.add_all(
        [
            GenerationProject(
                ceg="CEG-020",
                uf="SP",
                municipios=["Campinas"],
                potencia_outorgada_kw=100,
            ),
            GenerationProject(
                ceg="CEG-021", uf=None, municipios=None, potencia_outorgada_kw=999
            ),
            GenerationProject(
                ceg="CEG-022", uf="SP", municipios=None, potencia_outorgada_kw=999
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/geolocalizacao")
    data = response.json()

    assert data["total_municipios"] == 1
    assert data["dados"][0]["quantidade_projetos"] == 1
    assert data["dados"][0]["potencia_total"] == 100.0


async def test_geolocalizacao_response_vazio_quando_sem_dados(db_session, client):
    response = await client.get("/api/geolocalizacao")
    assert response.status_code == 200
    assert response.json() == {"total_municipios": 0, "dados": []}