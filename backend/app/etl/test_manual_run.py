"""
test_manual_run.py

Rodada manual ponta a ponta, para o item da checklist "testar rodada manual
ponta a ponta em ambiente local/staging". Isso NÃO substitui testes automatizados
(pytest) — é um script de inspeção humana, para você rodar uma vez, olhar a saída
e confirmar visualmente que o schema real bate com o documentado.

Uso:
    python -m etl.test_manual_run
    python -m etl.test_manual_run --raw-dir ./data/raw/siga
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .etl_siga_diario import run_siga_daily_download_safe


async def main(raw_dir: Path) -> None:
    print(f"Rodando download+validação SIGA. raw_dir={raw_dir.resolve()}\n")

    run = await run_siga_daily_download_safe(raw_dir)

    print("=" * 60)
    print(f"status:               {run.status.value if run.status else None}")
    print(f"iniciado_em:          {run.iniciado_em.isoformat()}")
    print(f"finalizado_em:        {run.finalizado_em.isoformat() if run.finalizado_em else None}")
    if run.iniciado_em and run.finalizado_em:
        elapsed = (run.finalizado_em - run.iniciado_em).total_seconds()
        print(f"duração:              {elapsed:.2f}s")
    print(f"linhas_processadas:   {run.linhas_processadas}")
    print("=" * 60)
    print("erros:")
    print(json.dumps(run.erros, indent=2, ensure_ascii=False, default=str))

    if run.status is not None and "falha" in run.status.value:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("./data/raw/siga"),
        help="Diretório onde os arquivos brutos por execução são salvos (default: ./data/raw/siga)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.raw_dir))