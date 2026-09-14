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
    # DeepSeek exposes an OpenAI-compatible API at this base URL.
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    # DeepSeek currently does not expose an embeddings endpoint. Keep this
    # optional so the provider template does not suggest an OpenAI model.
    embedding_model: str = ""
    courseware_rag_parser: str = "builtin"
    courseware_rag_chunk_size: int = 1200
    courseware_rag_chunk_overlap: int = 160
    courseware_rag_top_k: int = 5
    courseware_rag_working_dir: str = "backend/courseware_rag_data"
    search_provider_url: str = ""
    search_provider_key: str = ""
    clip_model_name: str = ""
    ppt_storage_dir: str = "backend/ppt_storage"
    ppt_generation_workers: int = 4
    ppt_generation_executor_workers: int = 4
    ppt_generation_poll_seconds: float = 3.0
    visual_search_mode: str = "browser_worker"
    visual_search_engine: str = "bing"
    visual_search_proxy: str = ""
    visual_search_timeout_seconds: int = 15
    visual_search_max_image_bytes: int = 8 * 1024 * 1024
    visual_search_max_pages: int = 0
    visual_search_max_concurrency: int = 3
    visual_search_browser_headless: bool = True
    visual_search_browser_executable_path: str = ""
    zoom_account_id: str = ""
    zoom_client_id: str = ""
    zoom_client_secret: str = ""
    zoom_host_user_id: str = "me"
    zoom_default_timezone: str = "Asia/Hong_Kong"
    zoom_sdk_client_id: str = ""
    zoom_sdk_key: str = ""
    zoom_sdk_secret: str = ""
    zoom_webhook_secret_token: str = ""
    zoom_webhook_verification_token: str = ""
    zoom_api_base_url: str = "https://api.zoom.us/v2"
    file_processing_dir: str = "backend/processed"
    file_processing_require_mineru: bool = True
    file_processing_mineru_command: str = "mineru"
    file_processing_max_bytes: int = 50 * 1024 * 1024
    file_processing_workers: int = 2
    file_processing_poll_seconds: float = 0.75
    file_processing_parser_version: str = "1"
    # Background task infrastructure.  The API keeps the database job row as
    # the source of truth; Celery/Redis is only the delivery mechanism.
    task_broker_url: str = "redis://localhost:6379/0"
    task_result_backend: str = "redis://localhost:6379/1"
    task_queue_enabled: bool = True
    task_queue_eager: bool = False
    task_max_retries: int = 3
    task_retry_backoff_seconds: int = 5

    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), extra="ignore")

    @staticmethod
    def _data_path(value: str) -> Path:
        """Resolve relative runtime paths from the repository root.

        The old implementation resolved ``backend/uploads`` relative to the
        process working directory.  Starting uvicorn from ``backend/`` then
        accidentally created ``backend/backend/uploads``.  Anchoring relative
        paths here makes CLI, tests and workers agree on one location.
        """
        path = Path(value)
        if path.is_absolute():
            return path
        root = Path(__file__).resolve().parents[3]
        return root / path

    @property
    def upload_path(self) -> Path:
        path = self._data_path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ppt_storage_path(self) -> Path:
        path = self._data_path(self.ppt_storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def file_processing_path(self) -> Path:
        path = self._data_path(self.file_processing_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
