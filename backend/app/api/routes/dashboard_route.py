"""
Endpoints de leitura para os painéis analíticos (Dashboards).

GET /api/kpis
GET /api/graficos/potencia-uf
GET /api/graficos/evolucao-anual
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# AJUSTE: Verifique os caminhos exatos das importações no seu projeto
from backend.app.db.session import get_db
from backend.app.core.auth_dependencies import get_current_user

from backend.app.schemas.dashboard_schema import (
    EvolucaoAnualResponse,
    KPIsResponse,
    PotenciaPorUFResponse,
)
from backend.app.schemas.filtros_schema import FiltrosQuery
from backend.app.services import dashboard_service

# Aplicando a proteção na raiz do router: TODAS as rotas exigirão o token/cookie
router = APIRouter(
    tags=["Dashboards"],
    dependencies=[Depends(get_current_user)]
)

@router.get(
    "/api/kpis",
    response_model=KPIsResponse,
    summary="Totalizadores e indicadores gerais do portfólio",
    description="Retorna os totalizadores. Regra de negócio: cliente_id não nulo. Ignora status_revisao."
)
async def obter_kpis(
    filtros: Annotated[FiltrosQuery, Query()],
    db: AsyncSession = Depends(get_db),
) -> KPIsResponse:
    return await dashboard_service.get_kpis(db, filtros)


@router.get(
    "/api/graficos/potencia-uf",
    response_model=PotenciaPorUFResponse,
    summary="Potência outorgada agrupada por UF",
)
async def obter_potencia_por_uf(
    filtros: Annotated[FiltrosQuery, Query()],
    db: AsyncSession = Depends(get_db),
) -> PotenciaPorUFResponse:
    dados = await dashboard_service.get_potencia_por_uf(db, filtros)
    return PotenciaPorUFResponse(dados=dados)


@router.get(
    "/api/graficos/evolucao-anual",
    response_model=EvolucaoAnualResponse,
    summary="Evolução anual da potência outorgada",
)
async def obter_evolucao_anual(
    filtros: Annotated[FiltrosQuery, Query()],
    db: AsyncSession = Depends(get_db),
) -> EvolucaoAnualResponse:
    dados = await dashboard_service.get_evolucao_anual(db, filtros)
    return EvolucaoAnualResponse(dados=dados)