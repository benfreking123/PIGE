from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "local"
    app_name: str = "usda-monitor"
    app_timezone: str = "America/Chicago"

    database_url: str = "postgresql+psycopg2://usda:usda@localhost:5432/usda_monitor"

    ses_region: str = "us-east-1"
    ses_sender: str = "noreply@example.com"
    master_alert_email: str = "alerts@example.com"
    email_enabled: bool = True

    poll_tick_seconds: int = 60
    max_concurrency: int = 4
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
