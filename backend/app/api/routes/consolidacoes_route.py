"""
Rotas de /api/consolidacoes, sobre consolidacoes_pendentes (README).

Protegida a nível de APIRouter via dependencies=[Depends(get_current_user)]
- mesmo padrão adotado para os próximos routers, conforme comentário em
main.py. Cada endpoint também injeta get_current_user individualmente
(FastAPI faz cache da dependency por request, não reexecuta) porque
aprovar/rejeitar precisam do id do usuário para preencher decidido_por.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.core.auth_dependencies import get_current_user
from backend.app.enum import ConsolidationStatus
from backend.app.schemas.consolidacoes_schema import ConsolidacaoAcaoOut, ConsolidacaoPendenteOut
from backend.app.schemas.filtros_schema import FiltrosQuery
from backend.app.services import consolidacoes_service

router = APIRouter(
    prefix="/api/consolidacoes",
    tags=["consolidacoes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/pendentes", response_model=list[ConsolidacaoPendenteOut])
async def listar_pendentes(
    filtros: Annotated[FiltrosQuery, Query()],
    db: AsyncSession = Depends(get_db),
) -> list[ConsolidacaoPendenteOut]:
    """Lista as pendências. Aceita os filtros da sidebar (origem, cliente, nome, uf, municipio, ano)."""
    itens = await consolidacoes_service.listar_pendentes(db, filtros)
    return [ConsolidacaoPendenteOut.model_validate(i) for i in itens]


@router.get("/decididas", response_model=list[ConsolidacaoPendenteOut])
async def listar_decididas(
    filtros: Annotated[FiltrosQuery, Query()],
    decisao: Annotated[
        Literal["aprovado", "rejeitado"] | None,
        Query(description="Restringe a aprovadas ou rejeitadas (padrão: ambas)"),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> list[ConsolidacaoPendenteOut]:
    """
    Histórico de consolidações de nome já decididas, da mais recente para a mais antiga.
    Serve de base para reabrir ou inverter uma decisão tomada por engano.
    """
    status_decisao = ConsolidationStatus(decisao) if decisao else None
    itens = await consolidacoes_service.listar_decididas(db, filtros, status_decisao)
    return [ConsolidacaoPendenteOut.model_validate(i) for i in itens]


@router.patch("/{item_id}/aprovar", response_model=ConsolidacaoAcaoOut)
async def aprovar(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> ConsolidacaoAcaoOut:
    usuario_id = UUID(usuario["sub"])
    item = await consolidacoes_service.aprovar_pendencia(db, item_id, usuario_id)
    return ConsolidacaoAcaoOut.model_validate(item)


@router.patch("/{item_id}/rejeitar", response_model=ConsolidacaoAcaoOut)
async def rejeitar(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> ConsolidacaoAcaoOut:
    usuario_id = UUID(usuario["sub"])
    item = await consolidacoes_service.rejeitar_pendencia(db, item_id, usuario_id)
    return ConsolidacaoAcaoOut.model_validate(item)


@router.patch("/{item_id}/reabrir", response_model=ConsolidacaoAcaoOut)
async def reabrir(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> ConsolidacaoAcaoOut:
    """Desfaz a decisão: a pendência volta para a fila e os projetos voltam a pendente, sem cliente."""
    item = await consolidacoes_service.reabrir_pendencia(db, item_id)
    return ConsolidacaoAcaoOut.model_validate(item)


@router.patch("/{item_id}/inverter", response_model=ConsolidacaoAcaoOut)
async def inverter(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> ConsolidacaoAcaoOut:
    """Troca a decisão (aprovada <-> rejeitada) numa única transação."""
    usuario_id = UUID(usuario["sub"])
    item = await consolidacoes_service.inverter_decisao(db, item_id, usuario_id)
    return ConsolidacaoAcaoOut.model_validate(item)