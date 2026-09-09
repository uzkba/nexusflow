import pytest
from backend.app.model.models import Client, RawName, PendingConsolidation
from backend.app.etl.matching import calcular_similaridade
from backend.app.services.consolidacao import salvar_sugestoes_em_massa
from sqlalchemy import select

@pytest.mark.asyncio
async def test_pipeline_geracao_e_bulk_insert(db_session):
    # 1. Cria um cliente oficial de teste no banco
    cliente = Client(nome_oficial="Empresa Solar S.A.")
    db_session.add(cliente)
    
    # 2. Cria um nome bruto parecido para o RapidFuzz pegar
    raw_name = RawName(nome_bruto="EMPRESA SOLAR S/A")
    db_session.add(raw_name)
    await db_session.flush()

    # 3. Busca os dados do banco para injetar no matching
    clientes_db = (await db_session.execute(select(Client))).scalars().all()
    nomes_db = (await db_session.execute(select(RawName))).scalars().all()

    # 4. Roda o algoritmo de similaridade (RapidFuzz)
    sugestoes = calcular_similaridade(nomes_db, clientes_db, threshold=80.0)
    
    assert len(sugestoes) == 1
    assert sugestoes[0]["score_similaridade"] >= 80.0

    # 5. Testa a função de Bulk Insert com tratamento de duplicatas
    inseridos_primeira = await salvar_sugestoes_em_massa(db_session, sugestoes)
    assert inseridos_primeira == 1

    # 6. Testa a regra de unicidade (tentar inserir a mesma sugestão de novo)
    inseridos_segunda = await salvar_sugestoes_em_massa(db_session, sugestoes)
    assert inseridos_segunda == 0  # Deve ignorar e retornar 0 devido ao on_conflict_do_nothing