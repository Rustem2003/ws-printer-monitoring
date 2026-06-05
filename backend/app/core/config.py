from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://printer:changeme_5432@postgres:5432/printerdb"
    redis_url: str = "redis://redis:6379/0"

    # JWT
    secret_key: str = "super-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # External services
    monitoring_service_url: str = "http://monitoring-service:9000"
    discovery_service_url: str = "http://discovery-service:9001"
    notification_service_url: str = "http://notification-service:9002"

    # Internal service-to-service auth (bypasses JWT)
    internal_token: str = ""

    # App
    environment: str = "production"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "allow"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
