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
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from .download_siga import DownloadResult, SigaDownloadError, download_siga_csv
from .load_and_validate import CsvLoadError, LoadResult, load_siga_csv
from .schema_siga import check_unknown_fase_origem_values

# Imports do nosso novo sistema de observabilidade no banco
from backend.app.services.etl_service import track_etl_run

logger = logging.getLogger("etl.siga_diario")


async def run_siga_daily_download(db: AsyncSession, raw_dir: Path) -> None:
    """Executa a rodada do SIGA injetando o status e os dados no PostgreSQL."""
    logger.info("Iniciando rodada SIGA diário")

    # Inicia o context manager (já cria log "em_andamento" no banco)
    async with track_etl_run(db) as etl_run:

        # ---------------------------------------------------------
        # ETAPA 1: Download
        # ---------------------------------------------------------
        try:
            download_result = await download_siga_csv(raw_dir=raw_dir)
            logger.info(
                "Download OK: %s (%d bytes, sha256=%s)",
                download_result.raw_path,
                download_result.size_bytes,
                download_result.sha256[:12],
            )
        except SigaDownloadError as exc:
            erro_log = {
                "tipo": "download",
                "mensagem": str(exc),
                "raw_file_salvo": False,
            }
            etl_run.erros = (etl_run.erros or []) + [erro_log]
            logger.error("Falha no download SIGA: %s", exc)
            raise  # Repassa para o track_etl_run marcar status='falha' no banco

        # ---------------------------------------------------------
        # ETAPA 2: Parse do CSV
        # ---------------------------------------------------------
        try:
            load_result = load_siga_csv(download_result.raw_path)
        except CsvLoadError as exc:
            erro_log = {
                "tipo": "csv_parse",
                "mensagem": str(exc),
                "raw_file_salvo": True,
                "raw_file_path": str(download_result.raw_path),
                "download_sha256": download_result.sha256,
            }
            etl_run.erros = (etl_run.erros or []) + [erro_log]
            logger.error("Falha ao ler/parsear CSV SIGA: %s", exc)
            raise

        # Atualiza a contagem de linhas no banco
        etl_run.linhas_processadas = load_result.row_count
        validation = load_result.column_validation

        # ---------------------------------------------------------
        # ETAPA 3: Validação de Schema (Colunas Críticas)
        # ---------------------------------------------------------
        if not validation.ok:
            erro_log = {
                "tipo": "schema_validation",
                "mensagem": "Coluna(s) crítica(s) ausente(s) no CSV da ANEEL",
                "colunas_criticas_ausentes": validation.missing_critical,
                "colunas_opcionais_ausentes": validation.missing_optional,
                "colunas_novas_inesperadas": validation.unexpected_new,
                "raw_file_salvo": True,
                "raw_file_path": str(download_result.raw_path),
                "download_sha256": download_result.sha256,
            }
            etl_run.erros = (etl_run.erros or []) + [erro_log]
            logger.error("Validação de schema falhou. Colunas críticas ausentes: %s", validation.missing_critical)
            # Ao lançar a exceção, o banco salva o erro estruturado e assume falha
            raise ValueError("Falha na validação do Schema (colunas críticas ausentes).")

        # ---------------------------------------------------------
        # ETAPA 4: Validação Opcional / Avisos (Não quebra o pipeline)
        # ---------------------------------------------------------
        valores_novos = check_unknown_fase_origem_values(
            load_result.df["DscFaseUsina"], load_result.df["DscOrigemCombustivel"]
        )
        tem_avisos = bool(
            validation.missing_optional or validation.unexpected_new or valores_novos.tem_valores_novos
        )
        
        if tem_avisos:
            aviso_log = {
                "tipo": "aviso_schema",
                "colunas_opcionais_ausentes": validation.missing_optional,
                "colunas_novas_inesperadas": validation.unexpected_new,
                **valores_novos.as_dict(),
            }
            etl_run.erros = (etl_run.erros or []) + [aviso_log]
            
            if valores_novos.tem_valores_novos:
                logger.warning("Valores novos de Fase/Origem detectados (fora da lista conhecida): %s", valores_novos.as_dict())

        logger.info(
            "Rodada SIGA concluída: linhas=%d, avisos=%s",
            etl_run.linhas_processadas,
            tem_avisos,
        )


async def run_siga_daily_download_safe(db: AsyncSession, raw_dir: Path):
    """
    Roda o pipeline de forma segura. Se o `track_etl_run` cuspir um erro (como foi 
    programado para fazer), este método captura e impede que a aplicação ou o APScheduler caiam.
    """
    try:
        await run_siga_daily_download(db, raw_dir)
    except Exception as exc:
        logger.critical("Falha tratada pelo safe_runner: %s", exc)


# ---------------------------------------------------------
# Permite rodar o script avulso pelo terminal para testes
# ---------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    from backend.app.db.session import get_db

    async def main():
        # Resolvemos a injeção de dependência do banco localmente
        async for db in get_db():
            raw_dir = Path("data/raw")
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            await run_siga_daily_download_safe(db, raw_dir)
            
    asyncio.run(main())