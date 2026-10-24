"""
Upsert de GenerationProject usando `ceg` como chave de conflito.

Decisões de negócio incorporadas aqui:
- `criado_em` e `ceg` nunca são sobrescritos pelo ETL.
- `cliente_id` é protegido: SÓ é sobrescrito se o `nome_bruto_principal_id`
  mudar no CSV (passando a assumir o valor novo mapeado pelo orquestrador).
- Se a linha já possuir um `status_revisao` no registro (ex: sentinela aprovado
  injetado pelo orquestrador), ele é respeitado; caso contrário, vai pra 'pendente'.
- A função NÃO comita a transação — só flush().
- A execução do upsert é separada em dois lotes para que o PostgreSQL consiga
  montar a cláusula SET correta (uma com cliente_id, outra sem).
"""

import datetime
import math
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.enum.projeto_geracao import ReviewStatus
from backend.app.model.models import GenerationProject


CAMPOS_QUE_IMPACTAM_GRAFICOS = {
    "potencia_outorgada_kw",
    "origem",
    "fase",
    "uf",
    "municipios",
    "inicio_vigencia_ano",
    "latitude",
    "longitude",
    "nome_bruto_principal_id",  # Adicionado
}

CAMPOS_NUMERICOS = {"potencia_outorgada_kw", "latitude", "longitude"}


def _valores_diferem(campo: str, antigo, novo) -> bool:
    """Campos numéricos (float) usam tolerância. Campos de texto usam igualdade direta."""
    if campo in CAMPOS_NUMERICOS:
        if antigo is None or novo is None:
            return antigo != novo
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
    `registros` é uma lista de dicts já normalizados e enriquecidos com
    `nome_bruto_principal_id` e `cliente_id`.
    """
    if not registros:
        return

    cegs = [r["ceg"] for r in registros]
    result = await session.execute(
        select(GenerationProject).where(GenerationProject.ceg.in_(cegs))
    )
    existentes_por_ceg = {p.ceg: p for p in result.scalars()}

    lote_mudou_dono = []
    lote_mesmo_dono = []

    for registro in registros:
        existente = existentes_por_ceg.get(registro["ceg"])

        if existente is None:
            # Novo projeto: status_revisao usa o do registro se existir, senao pendente
            registro["status_revisao"] = registro.get("status_revisao", ReviewStatus.pendente)
            registro["diff_pendente"] = None
            lote_mudou_dono.append(registro)  # Inserts entram no lote que grava cliente_id
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
            # Se já veio com status no registro (pode ser regra do orquestrador), respeita. Senao, pendente.
            registro["status_revisao"] = registro.get("status_revisao", ReviewStatus.pendente)
            registro["diff_pendente"] = diff
        else:
            registro["status_revisao"] = existente.status_revisao
            registro["diff_pendente"] = existente.diff_pendente

        # Direcionamento dos lotes: se o dono mudou, permitimos sobrescrever o cliente_id
        if "nome_bruto_principal_id" in diff:
            lote_mudou_dono.append(registro)
        else:
            lote_mesmo_dono.append(registro)

    colunas_dados = set(registros[0].keys())

    async def _executar_lote(lote: list[dict], permite_atualizar_cliente: bool):
        if not lote:
            return
            
        stmt = pg_insert(GenerationProject).values(lote)
        
        colunas_protegidas = {"ceg", "criado_em"}
        if not permite_atualizar_cliente:
            colunas_protegidas.add("cliente_id")
            
        colunas_atualizaveis = colunas_dados - colunas_protegidas
        
        # A chave ausente no registro original sequer entra em `colunas_dados`.
        # Só atualizamos as que vieram no payload e não estão protegidas.
        set_clause = {col: getattr(stmt.excluded, col) for col in colunas_atualizaveis if col in colunas_dados}
        set_clause["atualizado_em"] = func.now()

        stmt = stmt.on_conflict_do_update(index_elements=["ceg"], set_=set_clause)
        await session.execute(stmt)

    # Executa os dois fluxos na mesma transação
    await _executar_lote(lote_mudou_dono, permite_atualizar_cliente=True)
    await _executar_lote(lote_mesmo_dono, permite_atualizar_cliente=False)
    
    await session.flush()