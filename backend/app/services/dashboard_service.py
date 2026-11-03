"""
Camada de acesso a dados dos endpoints analíticos (KPIs e Gráficos).

Centraliza as condições usadas pelos endpoints para garantir que a regra de
negócio seja aplicada de forma consistente e não seja duplicada em cada
endpoint.
"""
from decimal import Decimal
from typing import List

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.app.core.constantes import SENTINELA_CLIENTE_ID
from backend.app.enum import ReviewStatus
from backend.app.model.models import Client, GenerationProject
from backend.app.schemas.filtros_schema import FiltrosQuery

# potencia_outorgada_kw vem em kW no banco; os endpoints expõem em MW.
KW_PARA_MW = 1000


def _sem_proprietario():
    """
    Projeto sem dono definido: ainda não consolidado (cliente_id NULL)
    ou atribuído ao cliente sentinela ("Não Informado").
    """
    return or_(
        GenerationProject.cliente_id.is_(None),
        GenerationProject.cliente_id == SENTINELA_CLIENTE_ID,
    )


def _com_proprietario():
    """Projeto com cliente real: cliente_id não nulo e diferente do sentinela."""
    return and_(
        GenerationProject.cliente_id.isnot(None),
        GenerationProject.cliente_id != SENTINELA_CLIENTE_ID,
    )


def _condicoes(filtros: FiltrosQuery | None = None) -> list:
    """
    Apenas os filtros da sidebar.

    REGRA DE NEGÓCIO
    ------------------------------------------------------------------
    Todo projeto do portfólio entra nos totais e gráficos, com ou sem
    cliente consolidado e independentemente de `status_revisao`.
    Projetos sem cliente são contados em "Sem Proprietário" até que o
    admin aprove a consolidação.
    ------------------------------------------------------------------
    """
    condicoes: list = []
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

    # Clientes reais: DISTINCT ignora NULL; o sentinela também é excluído
    total_clientes = await db.scalar(
        select(func.count(func.distinct(GenerationProject.cliente_id))).where(
            *condicoes, _com_proprietario()
        )
    )

    projetos_pendentes_revisao = await db.scalar(
        select(func.count())
        .select_from(GenerationProject)
        .where(*condicoes, GenerationProject.status_revisao == ReviewStatus.pendente)
    )

    # Sem proprietário: cliente_id NULL (ainda não consolidado) ou sentinela
    projetos_sem_proprietario = await db.scalar(
        select(func.count())
        .select_from(GenerationProject)
        .where(*condicoes, _sem_proprietario())
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
        # INNER JOIN é correto aqui; o sentinela não aparece como cliente no ranking
        .where(*_condicoes(filtros), _com_proprietario())
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