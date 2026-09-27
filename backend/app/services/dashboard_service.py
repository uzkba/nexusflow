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

from backend.app.enum import ReviewStatus
from backend.app.model.models import GenerationProject

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
       até que a revisão seja concluída. Isso é intencional — a revisão
       afeta a qualidade/confiança do dado, não a elegibilidade dele para
       compor os totais. Se alguém precisar de uma visão "apenas
       revisados", isso deve ser um filtro OPCIONAL e explícito em um novo
       endpoint/parâmetro — nunca o comportamento padrão destes três
       endpoints.
    ------------------------------------------------------------------
    """
    return GenerationProject.cliente_id.isnot(None)
    # Propositalmente SEM `GenerationProject.status_revisao == ...`


async def get_kpis(db: AsyncSession) -> dict:
    total_projetos = await db.scalar(
        select(func.count()).select_from(GenerationProject).where(_filtro_elegiveis())
    )

    potencia_total_kw = await db.scalar(
        select(func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0)).where(
            _filtro_elegiveis()
        )
    )

    total_clientes = await db.scalar(
        select(func.count(func.distinct(GenerationProject.cliente_id))).where(_filtro_elegiveis())
    )

    # Informativo apenas: quantos dos projetos elegíveis estão com revisão
    # pendente. NÃO é usado para excluir nada — ver comentário em _filtro_elegiveis().
    projetos_pendentes_revisao = await db.scalar(
        select(func.count())
        .select_from(GenerationProject)
        .where(_filtro_elegiveis(), GenerationProject.status_revisao == ReviewStatus.pendente)
    )

    return {
        "total_projetos": total_projetos or 0,
        "potencia_total_mw": Decimal(potencia_total_kw or 0) / KW_PARA_MW,
        "total_clientes": total_clientes or 0,
        "projetos_pendentes_revisao": projetos_pendentes_revisao or 0,
    }


async def get_potencia_por_uf(db: AsyncSession) -> List[dict]:
    stmt: Select = (
        select(
            GenerationProject.uf,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label(
                "potencia_total_kw"
            ),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .where(_filtro_elegiveis())
        .group_by(GenerationProject.uf)
        .order_by(func.sum(GenerationProject.potencia_outorgada_kw).desc())
    )

    resultado = await db.execute(stmt)

    return [
        {
            "uf": uf,
            "potencia_total": Decimal(potencia_total_kw or 0) / KW_PARA_MW,
            "total_projetos": total_projetos,
        }
        for uf, potencia_total_kw, total_projetos in resultado.all()
    ]


async def get_evolucao_anual(db: AsyncSession) -> List[dict]:
    stmt: Select = (
        select(
            GenerationProject.inicio_vigencia_ano,
            func.coalesce(func.sum(GenerationProject.potencia_outorgada_kw), 0).label(
                "potencia_total_kw"
            ),
            func.count(GenerationProject.ceg).label("total_projetos"),
        )
        .where(_filtro_elegiveis(), GenerationProject.inicio_vigencia_ano.isnot(None))
        .group_by(GenerationProject.inicio_vigencia_ano)
        .order_by(GenerationProject.inicio_vigencia_ano.asc())  # ordenação cronológica
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
                "potencia_total": potencia_total,
                "total_projetos": total_projetos,
                "potencia_acumulada": acumulado,
            }
        )

    return dados