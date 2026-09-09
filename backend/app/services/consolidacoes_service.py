"""
Camada de serviço do fluxo de aprovação unificado (/api/consolidacoes),
sobre PendingConsolidation em backend/app/model/models.py.

A rota permanece "burra": só chama estas funções e devolve o resultado.
Toda regra de negócio - inclusive a limpeza condicional de diff_pendente -
fica aqui.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import PendingConsolidation
from backend.app.enum import ConsolidationStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum


async def listar_pendentes(db: AsyncSession) -> list[PendingConsolidation]:
    """
    Retorna todas as linhas de consolidacoes_pendentes com status ==
    pendente, cobrindo tanto consolidacao_nome quanto alteracao_dado na
    mesma lista - a tela de aprovação não distingue os dois fluxos na
    consulta, só na exibição (via motivo_pendencia).

    selectinload é obrigatório aqui: cegs_relacionados é um relationship,
    e sem eager load o pydantic (fora do escopo async da sessão, dentro
    do model_validate na rota) dispara MissingGreenlet ao tentar acessá-lo.
    """
    resultado = await db.execute(
        select(PendingConsolidation)
        .options(selectinload(PendingConsolidation.cegs_relacionados))
        .where(PendingConsolidation.status == ConsolidationStatus.pendente)
    )
    return list(resultado.scalars().all())


async def _buscar_pendencia(db: AsyncSession, item_id: int) -> PendingConsolidation:
    resultado = await db.execute(
        select(PendingConsolidation)
        .options(selectinload(PendingConsolidation.cegs_relacionados))
        .where(PendingConsolidation.id == item_id)
    )
    item = resultado.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Pendência não encontrada"
        )
    if item.status != ConsolidationStatus.pendente:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Pendência já foi decidida",
        )
    return item


async def aprovar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Aprova a pendência independente do motivo, registrando quem decidiu.

    Regra de negócio central: diff_pendente só é limpo quando
    motivo_pendencia == alteracao_dado. Para consolidacao_nome, o campo
    permanece nulo (não é usado nesse fluxo).

    Fora de escopo aqui, de propósito: aplicar de fato a mudança (vincular
    nome_bruto.cliente_id ou sobrescrever o dado técnico em
    projetos_geracao) é responsabilidade de outra camada/serviço - este
    endpoint só decide a pendência.
    """
    item = await _buscar_pendencia(db, item_id)

    item.status = ConsolidationStatus.aprovado
    item.decidido_por = usuario_id
    item.decidido_em = datetime.now(timezone.utc)

    if item.motivo_pendencia == MotivoPendenciaEnum.alteracao_dado:
        # NULL, não {} - consistente com outras colunas JSONB do schema
        # (ex.: etl_runs.erros fica NULL quando não há erro a registrar)
        item.diff_pendente = None

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item


async def rejeitar_pendencia(
    db: AsyncSession, item_id: int, usuario_id: UUID
) -> PendingConsolidation:
    """
    Rejeita a pendência independente do motivo. diff_pendente é preservado
    para auditoria - só é limpo em aprovação de alteracao_dado, nunca em
    rejeição, para permitir revisão posterior do que foi recusado.
    """
    item = await _buscar_pendencia(db, item_id)

    item.status = ConsolidationStatus.rejeitado
    item.decidido_por = usuario_id
    item.decidido_em = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(item, attribute_names=["cegs_relacionados"])
    return item