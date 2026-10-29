import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.app.jobs.etl_jobs import scheduled_daily_etl_job
from backend.app.core.config_infra import infra_settings

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = AsyncIOScheduler()

def setup_scheduler() -> None:
    """
    Configures jobs and starts the scheduler.
    """
    # Add the ETL job using CRON expressions from environment variables
    scheduler.add_job(
        scheduled_daily_etl_job,
        trigger="cron",
        hour=infra_settings.ETL_CRON_HOUR,
        minute=infra_settings.ETL_CRON_MINUTE,
        id="siga_daily_etl",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(
        f"Scheduler started. Daily ETL configured to run at "
        f"{infra_settings.ETL_CRON_HOUR}:{infra_settings.ETL_CRON_MINUTE} (Cron)."
    )

def shutdown_scheduler() -> None:
    """
    Gracefully shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler gracefully shut down.")