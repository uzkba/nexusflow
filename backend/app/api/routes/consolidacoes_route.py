"""
Rotas de /api/consolidacoes, sobre consolidacoes_pendentes (README).

Protegida a nível de APIRouter via dependencies=[Depends(get_current_user)]
- mesmo padrão adotado para os próximos routers, conforme comentário em
main.py. Cada endpoint também injeta get_current_user individualmente
(FastAPI faz cache da dependency por request, não reexecuta) porque
aprovar/rejeitar precisam do id do usuário para preencher decidido_por.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.core.auth_dependencies import get_current_user
from backend.app.schemas.consolidacoes_schema import ConsolidacaoAcaoOut, ConsolidacaoPendenteOut
from backend.app.services import consolidacoes_service

router = APIRouter(
    prefix="/api/consolidacoes",
    tags=["consolidacoes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/pendentes", response_model=list[ConsolidacaoPendenteOut])
async def listar_pendentes(
    db: AsyncSession = Depends(get_db),
) -> list[ConsolidacaoPendenteOut]:
    itens = await consolidacoes_service.listar_pendentes(db)
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