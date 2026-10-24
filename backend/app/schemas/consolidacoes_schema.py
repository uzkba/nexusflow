from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.enum import ConsolidationStatus
from backend.app.enum.consolidacao import MotivoPendenciaEnum


class ConsolidacaoPendenteOut(BaseModel):
    """Item retornado por GET /api/consolidacoes/pendentes."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    motivo_pendencia: Optional[MotivoPendenciaEnum] = None
    status: ConsolidationStatus

    # Dados do Relacionamento
    nome_bruto_id: Optional[int] = None
    nome_bruto: Optional[str] = None
    cliente_sugerido_id: Optional[UUID] = None
    cliente_sugerido_nome: Optional[str] = None
    score_similaridade: Optional[float] = None
    cegs_relacionados: Optional[list[str]] = None

    # Agregados (Adicionados para a tela de decisão - Card C)
    ufs: list[str] = Field(default_factory=list)
    municipios: list[str] = Field(default_factory=list)
    total_projetos: int = 0
    potencia_total_mw: float = 0.0
    nomes_sugeridos_para_cliente: int = 0

    # Específico para alteracao_dado
    ceg: Optional[str] = None
    diff_pendente: Optional[dict[str, Any]] = None

    decidido_por: Optional[UUID] = None
    decidido_em: Optional[datetime] = None

    @field_validator("cegs_relacionados", mode="before")
    @classmethod
    def _extrair_ceg_do_relationship(cls, v: Any) -> Optional[list[str]]:
        if v is None:
            return None
        # Se por acaso já vier como lista de strings do service, deixa passar
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
            return v
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