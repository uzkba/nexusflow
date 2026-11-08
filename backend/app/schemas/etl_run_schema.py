from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

# Ajuste o import do Enum de acordo com o seu projeto
from backend.app.model.models import EtlRunStatus

class EtlRunResponse(BaseModel):
    id: int
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    status: EtlRunStatus
    linhas_processadas: int | None = None
    erros: list[dict[str, Any]] | None = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedEtlRunResponse(BaseModel):
    items: list[EtlRunResponse]
    total: int
    page: int
    size: int
    total_pages: int