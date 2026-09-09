"""
Testes de backend/app/etl/upsert_projetos_geracao.py

Sem factory própria no projeto (confirmado via grep em backend/tests/) —
os objetos GenerationProject são montados direto em cada teste.

Nota sobre isolamento: a fixture `db_session` (conftest.py) depende de
rollback por transação ao final de cada teste. upsert_projetos_geracao
foi ajustado para usar apenas flush() internamente — commitar aqui
quebraria esse isolamento entre testes.
"""
import math

import pytest
from sqlalchemy import select

from backend.app.enum.projeto_geracao import ReviewStatus
from backend.app.etl.upsert_projetos_geracao import upsert_projetos_geracao
from backend.app.model.models import GenerationProject


def _registro_base(ceg: str, **overrides) -> dict:
    base = {
        "ceg": ceg,
        "nome_projeto": "Usina Teste",
        "uf": "PB",
        "municipios": ["Campina Grande"],
        "origem": "Solar",
        "fase": "Construção não iniciada",
        "potencia_outorgada_kw": 1500.0,
        "inicio_vigencia_ano": 2026,
        "latitude": -7.230000,
        "longitude": -35.880000,
    }
    base.update(overrides)
    return base


async def _buscar(db_session, ceg: str) -> GenerationProject:
    # expire_all garante leitura fresca do banco — upsert_projetos_geracao
    # escreve via Core (ON CONFLICT), não via ORM, então a identity map
    # do session pode estar com o objeto pré-carregado internamente pela
    # própria função (o SELECT que ela faz pra montar o diff).
    db_session.expire_all()
    result = await db_session.execute(
        select(GenerationProject).where(GenerationProject.ceg == ceg)
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_insert_novo_fica_pendente_sem_diff(db_session):
    ceg = "TESTE.NOVO.0001"
    registros = [_registro_base(ceg)]

    await upsert_projetos_geracao(db_session, registros)

    projeto = await _buscar(db_session, ceg)
    assert projeto.status_revisao == ReviewStatus.pendente
    assert projeto.diff_pendente is None


@pytest.mark.asyncio
async def test_update_sem_mudanca_sensivel_preserva_status(db_session):
    ceg = "TESTE.SEMDIFF.0001"
    existente = GenerationProject(
        **_registro_base(ceg),
        status_revisao=ReviewStatus.aprovado,
        diff_pendente=None,
    )
    db_session.add(existente)
    await db_session.flush()

    # Muda só um campo que NÃO está em CAMPOS_QUE_IMPACTAM_GRAFICOS
    registro_novo = _registro_base(ceg, nome_projeto="Usina Teste (nome corrigido)")

    await upsert_projetos_geracao(db_session, [registro_novo])

    projeto = await _buscar(db_session, ceg)
    assert projeto.nome_projeto == "Usina Teste (nome corrigido)"
    assert projeto.status_revisao == ReviewStatus.aprovado
    assert projeto.diff_pendente is None


@pytest.mark.asyncio
async def test_update_com_mudanca_sensivel_volta_para_pendente(db_session):
    ceg = "TESTE.COMDIFF.0001"
    existente = GenerationProject(
        **_registro_base(ceg, potencia_outorgada_kw=1500.0),
        status_revisao=ReviewStatus.aprovado,
        diff_pendente=None,
    )
    db_session.add(existente)
    await db_session.flush()

    registro_novo = _registro_base(ceg, potencia_outorgada_kw=2000.0)

    await upsert_projetos_geracao(db_session, [registro_novo])

    projeto = await _buscar(db_session, ceg)
    assert projeto.potencia_outorgada_kw == 2000.0
    assert projeto.status_revisao == ReviewStatus.pendente
    assert projeto.diff_pendente == {
        "potencia_outorgada_kw": {"antigo": 1500.0, "novo": 2000.0}
    }


@pytest.mark.asyncio
async def test_ruido_de_float_nao_dispara_diff(db_session):
    ceg = "TESTE.RUIDOFLOAT.0001"
    latitude_original = -7.230000
    existente = GenerationProject(
        **_registro_base(ceg, latitude=latitude_original),
        status_revisao=ReviewStatus.aprovado,
        diff_pendente=None,
    )
    db_session.add(existente)
    await db_session.flush()

    # Diferença bem menor que abs_tol (1e-6) — não deve contar como mudança real
    ruido = 1e-9
    assert latitude_original != latitude_original + ruido, (
        "o teste precisa de um valor literalmente diferente, senão não testa nada"
    )

    registro_novo = _registro_base(ceg, latitude=latitude_original + ruido)

    await upsert_projetos_geracao(db_session, [registro_novo])

    projeto = await _buscar(db_session, ceg)
    assert projeto.status_revisao == ReviewStatus.aprovado
    assert projeto.diff_pendente is None


@pytest.mark.asyncio
async def test_cliente_id_nunca_e_sobrescrito_pelo_upsert(db_session):
    from backend.app.model.models import Client

    ceg = "TESTE.CLIENTEID.0001"
    cliente = Client(nome_oficial="Cliente Teste")
    db_session.add(cliente)
    await db_session.flush()

    existente = GenerationProject(
        **_registro_base(ceg),
        status_revisao=ReviewStatus.aprovado,
        diff_pendente=None,
        cliente_id=cliente.id,
    )
    db_session.add(existente)
    await db_session.flush()

    # Captura o valor puro AGORA — _buscar() chama expire_all(), que expira
    # também o objeto `cliente`, e ler cliente.id depois disso dispararia
    # um refresh síncrono inválido numa AsyncSession (MissingGreenlet).
    cliente_id_esperado = cliente.id

    # Registro do ETL não tem (e não deveria ter) cliente_id — o ETL não
    # sabe de consolidação de cliente, isso é decisão manual separada.
    registro_novo = _registro_base(ceg, potencia_outorgada_kw=9999.0)
    assert "cliente_id" not in registro_novo

    await upsert_projetos_geracao(db_session, [registro_novo])

    projeto = await _buscar(db_session, ceg)
    assert projeto.cliente_id == cliente_id_esperado, (
        "upsert sobrescreveu cliente_id — isso apagaria consolidação já aprovada"
    )