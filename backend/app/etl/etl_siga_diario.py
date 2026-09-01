"""
etl_siga_diario.py

Orquestra a rodada diária de download+load+validação do SIGA/ANEEL. Não faz
Transform nem Load no banco — isso é escopo de outra tarefa. O contrato deste
módulo termina em "temos um DataFrame validado ou sabemos exatamente por que não
temos".

Sobre "sem quebrar o pipeline": isso NÃO significa engolir toda exceção
silenciosamente. Significa que uma falha nesta rodada não deve derrubar o
processo do FastAPI/APScheduler nem impedir a próxima rodada agendada de rodar.
O resultado sempre carrega status + erro estruturado; quem chama decide o que
fazer (alertar, tentar de novo mais tarde, etc.).

"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .download_siga import DownloadResult, SigaDownloadError, download_siga_csv
from .load_and_validate import CsvLoadError, LoadResult, load_siga_csv
from .schema_siga import check_unknown_fase_origem_values

logger = logging.getLogger("etl.siga_diario")


class EtlRunStatus(str, Enum):

    EM_ANDAMENTO = "em_andamento"
    SUCESSO = "sucesso"
    ERRO = "erro"


@dataclass
class EtlRunRecord:

    iniciado_em: datetime
    finalizado_em: datetime | None = None
    status: EtlRunStatus = EtlRunStatus.EM_ANDAMENTO
    linhas_processadas: int | None = None
    erros: dict[str, Any] | None = None

    def as_etl_runs_row(self) -> dict[str, Any]:
        return {
            "iniciado_em": self.iniciado_em,
            "finalizado_em": self.finalizado_em,
            "status": self.status.value,
            "linhas_processadas": self.linhas_processadas,
            "erros": self.erros,
        }


async def run_siga_daily_download(raw_dir: Path) -> EtlRunRecord:
    run = EtlRunRecord(iniciado_em=datetime.now(timezone.utc))
    logger.info("Iniciando rodada SIGA diário em %s", run.iniciado_em.isoformat())

    download_result: DownloadResult | None = None

    try:
        download_result = await download_siga_csv(raw_dir=raw_dir)
        logger.info(
            "Download OK: %s (%d bytes, sha256=%s)",
            download_result.raw_path,
            download_result.size_bytes,
            download_result.sha256[:12],
        )
    except SigaDownloadError as exc:
        run.finalizado_em = datetime.now(timezone.utc)
        run.status = EtlRunStatus.ERRO
        run.erros = {
            "tipo": "download",
            "mensagem": str(exc),
            "raw_file_salvo": False,
        }
        logger.error("Falha no download SIGA: %s", exc)
        return run

    try:
        load_result = load_siga_csv(download_result.raw_path)
    except CsvLoadError as exc:
        run.finalizado_em = datetime.now(timezone.utc)
        run.status = EtlRunStatus.ERRO
        run.erros = {
            "tipo": "csv_parse",
            "mensagem": str(exc),
            "raw_file_salvo": True,
            "raw_file_path": str(download_result.raw_path),
            "download_sha256": download_result.sha256,
        }
        logger.error("Falha ao ler/parsear CSV SIGA: %s", exc)
        return run

    validation = load_result.column_validation
    run.finalizado_em = datetime.now(timezone.utc)
    run.linhas_processadas = load_result.row_count

    if not validation.ok:
        # Coluna crítica faltando: fatal para o pipeline seguir para Transform,
        # mas ainda não é uma exceção Python — é um status de negócio.
        run.status = EtlRunStatus.ERRO
        run.erros = {
            "tipo": "schema_validation",
            "mensagem": "Coluna(s) crítica(s) ausente(s) no CSV da ANEEL",
            "colunas_criticas_ausentes": validation.missing_critical,
            "colunas_opcionais_ausentes": validation.missing_optional,
            "colunas_novas_inesperadas": validation.unexpected_new,
            "raw_file_salvo": True,
            "raw_file_path": str(download_result.raw_path),
            "download_sha256": download_result.sha256,
        }
        logger.error(
            "Validação de schema falhou. Colunas críticas ausentes: %s",
            validation.missing_critical,
        )
        return run

    run.status = EtlRunStatus.SUCESSO

    valores_novos = check_unknown_fase_origem_values(
        load_result.df["DscFaseUsina"], load_result.df["DscOrigemCombustivel"]
    )
    tem_avisos = bool(
        validation.missing_optional or validation.unexpected_new or valores_novos.tem_valores_novos
    )
    if tem_avisos:
        run.erros = {
            "tipo": "aviso_schema",
            "colunas_opcionais_ausentes": validation.missing_optional,
            "colunas_novas_inesperadas": validation.unexpected_new,
            **valores_novos.as_dict(),
        }
        if valores_novos.tem_valores_novos:
            logger.warning(
                "Valores novos de Fase/Origem detectados (fora da lista conhecida): %s",
                valores_novos.as_dict(),
            )
    else:
        run.erros = None
    logger.info(
        "Rodada SIGA concluída: status=%s, linhas=%d, avisos=%s",
        run.status.value,
        run.linhas_processadas,
        tem_avisos,
    )
    return run


async def run_siga_daily_download_safe(raw_dir: Path) -> EtlRunRecord:
    try:
        return await run_siga_daily_download(raw_dir)
    except Exception as exc:  # noqa: BLE001 — intencional, é a guarda de última linha
        now = datetime.now(timezone.utc)
        logger.critical("Falha NÃO PREVISTA na rodada SIGA: %s\n%s", exc, traceback.format_exc())
        return EtlRunRecord(
            iniciado_em=now,
            finalizado_em=now,
            status=EtlRunStatus.ERRO,
            erros={
                "tipo": "unexpected",
                "mensagem": str(exc),
                "traceback": traceback.format_exc(),
            },
        )