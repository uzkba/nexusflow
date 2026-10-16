from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FiltrosQuery(BaseModel):
    origem: str | None = None
    cliente: UUID | None = None
    nome: str | None = None
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    municipio: str | None = None
    ano: int | None = None

    @field_validator("uf")
    @classmethod
    def uf_maiuscula(cls, v: str | None) -> str | None:
        return v.upper() if v else v