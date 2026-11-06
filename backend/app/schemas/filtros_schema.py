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


def normalizar_origem(valor: str | None) -> str | None:
    """
    Converte 'solar', 'SOLAR', 'eolica', 'Eólica', 'EOL' etc. para o valor gravado
    no banco ('Solar' / 'Eólica'). 'Todas'/'Todos'/vazio viram None (sem filtro).
    Qualquer outro valor passa como veio (sem espaços nas pontas).

    Função pública: reutilizada por todos os serviços que filtram por origem,
    para a regra existir em um único lugar.
    """
    if valor is None:
        return None
    chave = _sem_acento_minusculo(valor)
    if chave in _ORIGEM_SEM_FILTRO:
        return None
    return _ORIGEM_CANONICA.get(chave, valor.strip())


def padrao_contem(texto: str) -> str:
    """
    Padrão para ILIKE "contém": '%texto%', escapando \\, % e _ digitados pelo usuário
    (senão '50%' ou 'UFV_1' casariam com mais do que o digitado).
    Use com .ilike(padrao_contem(valor), escape="\\").
    """
    limpo = texto.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpo}%"


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
        return normalizar_origem(v)