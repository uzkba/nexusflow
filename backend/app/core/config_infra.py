"""
Infrastructure configuration: mandatory process dependencies (database).
Absence here crashes the boot — fails fast on module import.

DO NOT import this module in code that does not depend on infrastructure
(e.g., pure logic like matching/similarity.py). It was exactly this
coupling that caused fuzz matching tests to require DATABASE_URL/Docker
to run, for no real reason.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfraSettings(BaseSettings):
    # Database connection string (Required: Pydantic will fail fast if missing)
    DATABASE_URL: str

    # ETL Cron Settings (Defaults to 02:00 AM)
    ETL_CRON_HOUR: str = "2"
    ETL_CRON_MINUTE: str = "0"
    
    # Paths
    RAW_DATA_DIR: Path = Path("/tmp/nexusflow/raw")

    # Load variables from the .env file and ignore any extra variables
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


infra_settings = InfraSettings()