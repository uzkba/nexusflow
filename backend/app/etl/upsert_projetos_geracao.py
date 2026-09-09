"""
Upsert de GenerationProject usando `ceg` como chave de conflito.

Decisões de negócio incorporadas aqui (ver histórico da conversa / backlog):
- `cliente_id`, `criado_em` e `ceg` nunca são sobrescritos pelo ETL — pertencem
  ao fluxo de consolidação de cliente (manual) ou são imutáveis por definição.
- Se um CEG já existente vier com diferença em campos que impactam
  gráficos/KPIs, `status_revisao` volta para 'pendente' e o diff é registrado
  em `diff_pendente` (JSONB) para a tela de aprovação (Card 13/24) mostrar
  o que mudou.
- Comparação de campo numérico (`potencia_outorgada_kw`, tipo Float) usa
  tolerância (math.isclose) para não gerar diff fantasma por erro de ponto
  flutuante. Campos de texto usam igualdade direta.
- Endpoints de gráficos/KPIs NÃO filtram por status_revisao (decisão
  registrada: opção 2 — o pendente aqui é só sinalizador para revisão
  posterior, sem efeito imediato no que aparece no dashboard).
- A função NÃO comita a transação — só flush(). Quem chama decide quando
  commitar (necessário para compatibilidade com fixtures de teste
  baseadas em rollback por transação).

Pendente de validação: o valor de abs_tol abaixo (1e-6) foi escolhido para
absorver só ruído de representação float, não diferença real de medição —
validar contra dados reais da ANEEL antes de confiar cegamente nisso.
"""

import datetime
import math
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.enum.projeto_geracao import ReviewStatus
from backend.app.model.models import GenerationProject

COLUNAS_PROTEGIDAS = {"ceg", "cliente_id", "criado_em"}

CAMPOS_QUE_IMPACTAM_GRAFICOS = {
    "potencia_outorgada_kw",
    "origem",
    "fase",
    "uf",
    "municipios",
    "inicio_vigencia_ano",  # alimenta /api/graficos/evolucao-anual
    "latitude",             # alimenta o mapa (Card 17/23)
    "longitude",            # alimenta o mapa (Card 17/23)
}
# inicio_vigencia_ano é integer — igualdade direta já é segura, não precisa
# de tolerância. latitude/longitude são double precision — mesmo tratamento
# de tolerância que potencia_outorgada_kw, por serem float.
CAMPOS_NUMERICOS = {"potencia_outorgada_kw", "latitude", "longitude"}


def _valores_diferem(campo: str, antigo, novo) -> bool:
    """
    Campos numéricos (float) usam tolerância pra não gerar diff fantasma
    por erro de ponto flutuante (armazenamento/leitura no Postgres, cast
    do Pandas, etc). Campos de texto usam igualdade direta.
    """
    if campo in CAMPOS_NUMERICOS:
        if antigo is None or novo is None:
            return antigo != novo
        # abs_tol bem apertado — só absorve ruído de float, não diferença real
        return not math.isclose(antigo, novo, rel_tol=1e-9, abs_tol=1e-6)
    return antigo != novo


def _serializavel(valor):
    """JSONB não aceita Decimal/datetime direto — converte pra tipo seguro."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.isoformat()
    return valor


async def upsert_projetos_geracao(
    session: AsyncSession, registros: list[dict]
) -> None:
    """
    Upsert em lote de GenerationProject usando `ceg` como chave de conflito.
    `registros` é uma lista de dicts já normalizados pelo Transform
    (mesmas chaves = mesmas colunas em todos os itens).
    """
    if not registros:
        return

    cegs = [r["ceg"] for r in registros]
    result = await session.execute(
        select(GenerationProject).where(GenerationProject.ceg.in_(cegs))
    )
    existentes_por_ceg = {p.ceg: p for p in result.scalars()}

    for registro in registros:
        existente = existentes_por_ceg.get(registro["ceg"])

        if existente is None:
            registro["status_revisao"] = ReviewStatus.pendente
            registro["diff_pendente"] = None
            continue

        diff = {}
        for campo in CAMPOS_QUE_IMPACTAM_GRAFICOS:
            if campo not in registro:
                continue
            valor_antigo = getattr(existente, campo)
            valor_novo = registro[campo]
            if _valores_diferem(campo, valor_antigo, valor_novo):
                diff[campo] = {
                    "antigo": _serializavel(valor_antigo),
                    "novo": _serializavel(valor_novo),
                }

        if diff:
            registro["status_revisao"] = ReviewStatus.pendente
            registro["diff_pendente"] = diff
        else:
            registro["status_revisao"] = existente.status_revisao
            registro["diff_pendente"] = existente.diff_pendente

    colunas_dados = set(registros[0].keys())
    colunas_atualizaveis = colunas_dados - COLUNAS_PROTEGIDAS

    stmt = pg_insert(GenerationProject).values(registros)
    set_clause = {col: getattr(stmt.excluded, col) for col in colunas_atualizaveis}
    set_clause["atualizado_em"] = func.now()

    stmt = stmt.on_conflict_do_update(index_elements=["ceg"], set_=set_clause)
    await session.execute(stmt)
    await session.flush()
    # Commit é responsabilidade de quem chama (endpoint, orquestrador do
    # pipeline, ou o teste) — não da função de service. Comitar aqui
    # dentro quebra fixtures de teste baseadas em rollback por transação.