from __future__ import annotations

import unicodedata
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Valores canônicos gravados pelo ETL em projetos_geracao.origem
_ORIGEM_CANONICA = {
    "solar": "Solar",
    "ufv": "Solar",
    "eolica": "Eólica",
    "eol": "Eólica",
}
# Valores que significam "sem filtro"
_ORIGEM_SEM_FILTRO = {"", "todas", "todos", "all"}


def _sem_acento_minusculo(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto.strip())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").lower()


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

    @field_validator("origem")
    @classmethod
    def origem_canonica(cls, v: str | None) -> str | None:
        """Aceita 'solar', 'SOLAR', 'eolica', 'Eólica' etc. e devolve o valor gravado no banco."""
        if v is None:
            return v
        chave = _sem_acento_minusculo(v)
        if chave in _ORIGEM_SEM_FILTRO:
            return None
        return _ORIGEM_CANONICA.get(chave, v.strip())