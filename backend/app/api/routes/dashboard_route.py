"""
Endpoints de leitura para os painéis analíticos (Dashboards).

GET /api/kpis
GET /api/graficos/potencia-uf
GET /api/graficos/evolucao-anual
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 🔧 AJUSTE ESTA LINHA: caminho real do seu session.py (o que define get_db)
from backend.app.db.session import get_db

from backend.app.schemas.dashboard_schema import (
    EvolucaoAnualResponse,
    KPIsResponse,
    PotenciaPorUFResponse,
)
from backend.app.services import dashboard_service

router = APIRouter(tags=["Dashboards"])


@router.get(
    "/api/kpis",
    response_model=KPIsResponse,
    summary="Totalizadores e indicadores gerais do portfólio",
    description=(
        "Retorna os totalizadores do Painel Executivo.\n\n"
        "**Regra de negócio:** considera apenas projetos com `cliente_id` "
        "preenchido. Projetos com pendência de revisão técnica "
        "(`status_revisao = pendente`) **são incluídos** nos totais — a "
        "pendência é informada separadamente no campo "
        "`projetos_pendentes_revisao`, mas não remove o projeto dos demais "
        "totais."
    ),
)
async def obter_kpis(db: AsyncSession = Depends(get_db)) -> KPIsResponse:
    return await dashboard_service.get_kpis(db)


@router.get(
    "/api/graficos/potencia-uf",
    response_model=PotenciaPorUFResponse,
    summary="Potência outorgada agrupada por UF",
    description=(
        "Retorna a soma da potência outorgada (MW) agrupada por Estado (UF), "
        "ordenada da maior para a menor potência.\n\n"
        "Aplica a mesma regra de elegibilidade de `/api/kpis` "
        "(`cliente_id IS NOT NULL`, sem filtro de `status_revisao`)."
    ),
)
async def obter_potencia_por_uf(db: AsyncSession = Depends(get_db)) -> PotenciaPorUFResponse:
    dados = await dashboard_service.get_potencia_por_uf(db)
    return PotenciaPorUFResponse(dados=dados)


@router.get(
    "/api/graficos/evolucao-anual",
    response_model=EvolucaoAnualResponse,
    summary="Evolução anual da potência outorgada",
    description=(
        "Retorna a soma da potência outorgada (MW) agrupada por ano de "
        "início de vigência, ordenada cronologicamente, incluindo a "
        "potência acumulada até cada ano.\n\n"
        "Aplica a mesma regra de elegibilidade de `/api/kpis` "
        "(`cliente_id IS NOT NULL`, sem filtro de `status_revisao`)."
    ),
)
async def obter_evolucao_anual(db: AsyncSession = Depends(get_db)) -> EvolucaoAnualResponse:
    dados = await dashboard_service.get_evolucao_anual(db)
    return EvolucaoAnualResponse(dados=dados)