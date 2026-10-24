"""
Camada de acesso a dados dos endpoints analíticos (KPIs e Gráficos).

Centraliza a query "base" usada pelos três endpoints para garantir que a
regra de negócio crítica seja aplicada de forma consistente e não seja
duplicada (e, portanto, não seja esquecida) em cada endpoint.
"""
from decimal import Decimal
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.app.core.constantes import SENTINELA_CLIENTE_ID
from backend.app.enum import ReviewStatus
from backend.app.model.models import Client, GenerationProject
from backend.app.schemas.filtros_schema import FiltrosQuery

# potencia_outorgada_kw vem em kW no banco; os endpoints expõem em MW.
KW_PARA_MW = 1000


def _filtro_elegiveis():
    """
    Condição de filtro BASE usada por todos os endpoints de KPIs/Gráficos.

    ⚠️ REGRA DE NEGÓCIO — NÃO ALTERAR SEM ALINHAR COM O PRODUTO ⚠️
    ------------------------------------------------------------------
    1) Filtramos APENAS por `cliente_id IS NOT NULL`. Projetos sem cliente
       vinculado (ex: dados brutos ainda não consolidados/atribuídos) não
       devem entrar em nenhum totalizador ou gráfico.

    2) NÃO filtramos por `status_revisao`. Um projeto com pendência de
       revisão de dado técnico É UM DADO VÁLIDO para fins de portfólio e
       DEVE continuar sendo contado normalmente nos KPIs e nos gráficos
       até que a revisão seja concluída.
    ------------------------------------------------------------------
    """
    return GenerationProject.cliente_id.isnot(None)


def _condicoes(filtros: FiltrosQuery | None = None) -> list:
    """
    Regra de elegibilidade (_filtro_elegiveis) + filtros da sidebar.
    """
    condicoes = [_filtro_elegiveis()]
    if filtros is None:
        return condicoes

    if filtros.origem:
        condicoes.append(GenerationProject.origem == filtros.origem)
    if filtros.cliente:
        condicoes.append(GenerationProject.cliente_id == filtros.cliente)
    if filtros.nome:
        condicoes.append(GenerationProject.nome_projeto == filtros.nome)
    if filtros.uf:
        condicoes.append(GenerationProject.uf == filtros.uf)
    if filtros.municipio:
        # municipios é JSONB list[str]: contenção (@>), não igualdade
        condicoes.append(GenerationProject.municipios.contains([filtros.municipio]))
    if filtros.ano:
        condicoes.append(GenerationProject.inicio_vigencia_ano == filtros.ano)
    return condicoes


async def get_kpis(db: AsyncSession, filtros: FiltrosQuery | None = None) -> dict:
    condicoes = _condicoes(filtros)

    total_projetos = await db.scalar(
        select(func.count()).select_from(GenerationProject).where(*condicoes)
    )

    potencia_total_kw = await db.scalar(
        select(func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0)).where(
            *condicoes
        )
    )

    # Exclui o sentinela da contagem real de clientes
    total_clientes = await db.scalar(
        select(func.count(func.distinct(GenerationProject.cliente_id))).where(
            *condicoes,
            GenerationProject.cliente_id != SENTINELA_CLIENTE_ID
        )
    )

    projetos_pendentes_revisao = await db.scalar(
        select(func.count())
        .select_from(GenerationProject)
        .where(*condicoes, GenerationProject.status_revisao == ReviewStatus.pendente)
    )

    # Conta separadamente os projetos que caíram no sentinela
    projetos_sem_proprietario = await db.scalar(
        select(func.count())
        .select_from(GenerationProject)
        .where(*condicoes, GenerationProject.cliente_id == SENTINELA_CLIENTE_ID)
    )

    return {
        "total_projetos": total_projetos or 0,
        "potencia_total_mw": float(Decimal(potencia_total_kw or 0) / KW_PARA_MW),
        "total_clientes": total_clientes or 0,
        "projetos_pendentes_revisao": projetos_pendentes_revisao or 0,
        "projetos_sem_proprietario": projetos_sem_proprietario or 0,
    }


async def get_potencia_por_uf(
    db: AsyncSession, filtros: FiltrosQuery | None = None
) -> List[dict]:
    stmt: Select = (
        select(
            GenerationProject.uf,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label(
                "potencia_total_kw"
            ),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .where(*_condicoes(filtros))
        .group_by(GenerationProject.uf)
        .order_by(func.sum(GenerationProject.potencia_outorgada_kw).desc())
    )

    resultado = await db.execute(stmt)

    return [
        {
            "uf": uf,
            "potencia_total": float(Decimal(potencia_total_kw or 0) / KW_PARA_MW),
            "total_projetos": total_projetos,
        }
        for uf, potencia_total_kw, total_projetos in resultado.all()
    ]


async def get_evolucao_anual(
    db: AsyncSession, filtros: FiltrosQuery | None = None
) -> List[dict]:
    stmt: Select = (
        select(
            GenerationProject.inicio_vigencia_ano,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label(
                "potencia_total_kw"
            ),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .where(*_condicoes(filtros), GenerationProject.inicio_vigencia_ano.isnot(None))
        .group_by(GenerationProject.inicio_vigencia_ano)
        .order_by(GenerationProject.inicio_vigencia_ano.asc())
    )

    resultado = await db.execute(stmt)

    dados = []
    acumulado = Decimal(0)
    for ano, potencia_total_kw, total_projetos in resultado.all():
        potencia_total = Decimal(potencia_total_kw or 0) / KW_PARA_MW
        acumulado += potencia_total
        dados.append(
            {
                "ano": int(ano),
                "potencia_total": float(potencia_total),
                "total_projetos": total_projetos,
                "potencia_acumulada": float(acumulado),
            }
        )

    return dados


async def get_origem(
    db: AsyncSession, filtros: FiltrosQuery | None = None
) -> list[dict]:
    """Retorna potência e quantidade por tipo de geração (Solar vs Eólica)."""
    stmt = (
        select(
            GenerationProject.origem,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label("potencia_total_kw"),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .where(*_condicoes(filtros))
        .group_by(GenerationProject.origem)
        .order_by(func.sum(GenerationProject.potencia_outorgada_kw).desc())
    )

    resultado = await db.execute(stmt)

    return [
        {
            "origem": origem,
            "potencia_total_mw": float(Decimal(potencia_total_kw or 0) / KW_PARA_MW),
            "total_projetos": total_projetos,
        }
        for origem, potencia_total_kw, total_projetos in resultado.all()
    ]


async def get_ranking_clientes(
    db: AsyncSession, limite: int = 20, filtros: FiltrosQuery | None = None
) -> list[dict]:
    """Retorna os top clientes ordenados por potência outorgada total."""
    
    limite_seguro = min(max(1, limite), 100)

    stmt = (
        select(
            Client.id,
            Client.nome_oficial,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label("potencia_total_kw"),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .join(Client, GenerationProject.cliente_id == Client.id)
        .where(*_condicoes(filtros))
        .group_by(Client.id, Client.nome_oficial)
        .order_by(func.sum(GenerationProject.potencia_outorgada_kw).desc())
        .limit(limite_seguro)
    )

    resultado = await db.execute(stmt)

    return [
        {
            "cliente_id": cliente_id,
            "nome_oficial": nome_oficial,
            "potencia_total_mw": float(Decimal(potencia_total_kw or 0) / KW_PARA_MW),
            "total_projetos": total_projetos,
        }
        for cliente_id, nome_oficial, potencia_total_kw, total_projetos in resultado.all()
    ]