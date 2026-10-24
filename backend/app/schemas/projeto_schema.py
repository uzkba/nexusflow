# backend/app/schemas/projeto_schema.py
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
    
    # ReviewStatus é um Enum do SQLAlchemy. 
    # Validamos como string no frontend, pois o FastAPI serializa Enums nativamente para string.
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