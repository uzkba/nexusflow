import logging
from sqlalchemy.ext.asyncio import AsyncSession
# Adjust the imports according to your project structure
from backend.app.db.session import AsyncSessionLocal 
from backend.app.core.config_infra import infra_settings
from backend.app.etl.etl_siga_diario import run_siga_daily_download_safe
logger = logging.getLogger(__name__)

async def scheduled_daily_etl_job() -> None:
    """
    Background job to run the daily SIGA ETL pipeline.
    It provisions an isolated asynchronous database session to prevent connection leaks.
    """
    logger.info("Starting scheduled daily ETL job...")
    
    # CRITICAL: Context manager ensures the session is closed and returned to the pool
    try:
        async with AsyncSessionLocal() as session:
            infra_settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
            await run_siga_daily_download_safe(db=session, raw_dir=infra_settings.RAW_DATA_DIR)
            
        logger.info("Successfully finished scheduled daily ETL job.")
        
    except Exception as e:
        logger.error(f"Scheduled ETL job failed with error: {e}", exc_info=True)
        # The session is safely rolled back and closed automatically by the context manager