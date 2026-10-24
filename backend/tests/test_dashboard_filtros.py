import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import GenerationProject, Client
from backend.app.enum import ReviewStatus
from backend.app.core.auth_dependencies import get_current_user
from backend.main import app

@pytest.fixture
async def mock_projetos(db_session: AsyncSession):
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()

    # 1. CRIA OS CLIENTES PRIMEIRO
    cliente1 = Client(id=c1, nome_oficial="Cliente Um") 
    cliente2 = Client(id=c2, nome_oficial="Cliente Dois")
    db_session.add_all([cliente1, cliente2])
    await db_session.commit()

    # 2. CRIA OS PROJETOS VINCULADOS
    projetos = [
        GenerationProject(
            ceg="UFV-1", nome_projeto="Solar 1", cliente_id=c1, uf="MG",
            municipios=["Belo Horizonte"], origem="solar", fase="Operação", inicio_vigencia_ano=2024,
            potencia_outorgada_kw=1000.0, status_revisao=ReviewStatus.aprovado
        ),
        GenerationProject(
            ceg="UFV-2", nome_projeto="Solar 2", cliente_id=c1, uf="BA",
            municipios=["Salvador"], origem="solar", fase="Operação", inicio_vigencia_ano=2024,
            potencia_outorgada_kw=2000.0, status_revisao=ReviewStatus.pendente
        ),
        GenerationProject(
            ceg="UFV-3", nome_projeto="Solar Lixo", cliente_id=None, uf="MG",
            municipios=["Uberlândia"], origem="solar", fase="Operação", inicio_vigencia_ano=2024,
            potencia_outorgada_kw=5000.0, status_revisao=ReviewStatus.aprovado
        ),
        GenerationProject(
            ceg="EOL-1", nome_projeto="Eólica 1", cliente_id=c2, uf="CE",
            municipios=["Fortaleza", "Caucaia"], origem="eolica", fase="Operação", inicio_vigencia_ano=2025,
            potencia_outorgada_kw=3000.0, status_revisao=ReviewStatus.aprovado
        )
    ]
    db_session.add_all(projetos)
    await db_session.commit()
    
    return {"c1": c1, "c2": c2}

@pytest.mark.asyncio
async def test_kpis_regras_base_e_filtros(client: AsyncClient, mock_projetos: dict, usuario_ativo):
    # Faz o override da autenticação para o teste passar no Depends(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: usuario_ativo
    
    try:
        # TESTE 1: Sem filtros (Verifica regra base)
        resp = await client.get("/api/kpis")
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["total_projetos"] == 3
        assert float(data["potencia_total_mw"]) == 6.0
        assert data["projetos_pendentes_revisao"] == 1

        # TESTE 2: Filtro por UF (MG)
        resp = await client.get("/api/kpis?uf=MG")
        assert resp.json()["total_projetos"] == 1

        # TESTE 3: Filtro por Município (Contenção JSONB)
        resp = await client.get("/api/kpis?municipio=Caucaia")
        assert resp.json()["total_projetos"] == 1
        assert float(resp.json()["potencia_total_mw"]) == 3.0

        # TESTE 4: Filtro por Cliente (UUID)
        resp = await client.get(f"/api/kpis?cliente={mock_projetos['c1']}")
        assert resp.json()["total_projetos"] == 2

    finally:
        # Limpa o override para não afetar outros testes
        app.dependency_overrides.pop(get_current_user, None)