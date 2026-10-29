import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import EtlRun
from backend.app.enum.etl import EtlRunStatus

@asynccontextmanager
async def track_etl_run(db: AsyncSession):
    """
    Context manager para rastrear a execução do ETL.
    Uso:
        async with track_etl_run(db) as etl_run:
            ... lógica do ETL ...
            etl_run.linhas_processadas = 1500
    """
    etl_run = EtlRun(status=EtlRunStatus.em_andamento)
    db.add(etl_run)
    await db.commit()
    await db.refresh(etl_run)

    try:
        yield etl_run
        etl_run.status = EtlRunStatus.sucesso
        
    except Exception as e:
        etl_run.status = EtlRunStatus.erro
        
        erro_log = {
            "error_type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        
        # Como é uma list[dict], garantimos que o log de erro será adicionado à lista.
        # Criar uma nova lista força o SQLAlchemy a detectar a alteração no campo JSONB.
        etl_run.erros = (etl_run.erros or []) + [erro_log]
        
        raise
    finally:
        etl_run.finalizado_em = datetime.now(timezone.utc)
        await db.commit()