"""
Schemas Pydantic para /api/consolidacoes, sobre PendingConsolidation
(tabela consolidacoes_pendentes) em backend/app/model/models.py.

Ajustado ao model real:
- Sem criado_em (a tabela não tem essa coluna).
- cegs_relacionados é um relationship para ConsolidationCeg, não uma
  lista de strings crua - o validator abaixo extrai o campo `ceg` de
  cada objeto relacionado antes da validação normal do pydantic.
- status e motivo_pendencia usam os Enums reais do projeto
  (ConsolidationStatus, MotivoPendenciaEnum), não Enums próprios do
  schema, para não duplicar/dessincronizar valores.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from backend.app.enum import ConsolidationStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum


class ConsolidacaoPendenteOut(BaseModel):
    """Item retornado por GET /api/consolidacoes/pendentes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    motivo_pendencia: Optional[MotivoPendenciaEnum] = None
    status: ConsolidationStatus

    # Preenchidos apenas quando motivo_pendencia == consolidacao_nome
    nome_bruto_id: Optional[int] = None
    cliente_sugerido_id: Optional[UUID] = None
    score_similaridade: Optional[float] = None
    cegs_relacionados: Optional[list[str]] = None

    # Preenchidos apenas quando motivo_pendencia == alteracao_dado
    ceg: Optional[str] = None
    diff_pendente: Optional[dict[str, Any]] = None

    decidido_por: Optional[UUID] = None
    decidido_em: Optional[datetime] = None

    @field_validator("cegs_relacionados", mode="before")
    @classmethod
    def _extrair_ceg_do_relationship(cls, v: Any) -> Optional[list[str]]:
        """
        `v` chega aqui como list[ConsolidationCeg] (o relationship real),
        não list[str]. Extrai o campo .ceg de cada objeto - se algum dia
        vier já como string (ex.: em algum teste unitário que monte o
        schema direto de um dict), passa direto sem quebrar.
        """
        if v is None:
            return None
        return [item.ceg if hasattr(item, "ceg") else item for item in v]


class ConsolidacaoAcaoOut(BaseModel):
    """Retorno padrão de /aprovar e /rejeitar."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    motivo_pendencia: Optional[MotivoPendenciaEnum] = None
    status: ConsolidationStatus
    diff_pendente: Optional[dict[str, Any]] = None
    decidido_por: Optional[UUID] = None
    decidido_em: Optional[datetime] = None