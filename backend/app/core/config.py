from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    app_name: str = "awa-intelligence-api"
    database_url: str = "sqlite:///./local.db"
    raw_storage_mode: str = "local"
    raw_storage_root: str = "storage/raw"
    ingestion_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def get_database_url():
    database_url = settings.database_url

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url
