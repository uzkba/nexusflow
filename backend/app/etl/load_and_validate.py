
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .schema_siga import ColumnValidationResult, validate_columns


CSV_SEP = ";"
CSV_DECIMAL = ","
CSV_ENCODING = "utf-8"


class CsvLoadError(Exception):
    """Erro ao carregar o CSV em DataFrame — arquivo malformado, encoding errado, etc."""


@dataclass
class LoadResult:
    df: pd.DataFrame
    row_count: int
    column_validation: ColumnValidationResult


def load_siga_csv(raw_path: Path) -> LoadResult:
    try:
        df = pd.read_csv(
            raw_path,
            sep=CSV_SEP,
            decimal=CSV_DECIMAL,
            encoding=CSV_ENCODING,
            dtype=str,  # carrega tudo como string nesta etapa; conversão de tipo é Transform
            quotechar='"',
        )
    except pd.errors.EmptyDataError as exc:
        raise CsvLoadError(f"CSV vazio ou sem cabeçalho: {raw_path}") from exc
    except pd.errors.ParserError as exc:
        raise CsvLoadError(f"CSV malformado (erro de parsing): {raw_path} — {exc}") from exc
    except UnicodeDecodeError as exc:
        raise CsvLoadError(
            f"Falha de encoding ao ler {raw_path} como {CSV_ENCODING}. "
            f"A ANEEL pode ter trocado o encoding do arquivo — verificar manualmente."
        ) from exc

    if df.empty:
        raise CsvLoadError(f"CSV carregado sem nenhuma linha de dados: {raw_path}")

    validation = validate_columns(list(df.columns))

    return LoadResult(df=df, row_count=len(df), column_validation=validation)