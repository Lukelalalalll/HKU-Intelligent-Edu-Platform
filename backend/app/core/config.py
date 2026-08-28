from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://hku:hku_dev_password@localhost:5432/hku_edu"
    jwt_secret_key: str = "change-this-development-secret"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 14
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"
    upload_dir: str = "backend/uploads"
    demo_accounts_enabled: bool = True

    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), extra="ignore")

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

