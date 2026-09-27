"""
Schemas Pydantic do endpoint GET /api/projetos

Espelha o model real `GenerationProject` (tabela `projetos_geracao`).
PK é `ceg` (Código Único ANEEL, string) — não há coluna `id` incremental.
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ProjetoOut(BaseModel):
    """Representação de um projeto de geração retornado pela listagem."""

    model_config = ConfigDict(from_attributes=True)

    ceg: str
    nome_projeto: str | None = None
    cliente_id: uuid.UUID | None = None
    uf: str | None = None
    municipios: list[str] | None = None
    origem: str | None = None
    fase: str | None = None
    potencia_outorgada_kw: float | None = None
    inicio_vigencia_ano: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    # ReviewStatus é um Enum do SQLAlchemy — se ele NÃO herdar de `str`
    # (i.e. não for `class ReviewStatus(str, Enum)`), troque o tipo abaixo
    # pelo Enum real (`status_revisao: ReviewStatus`) para validar certo.
    status_revisao: str
    criado_em: datetime
    atualizado_em: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope padrão de paginação usado por todos os endpoints de listagem."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int