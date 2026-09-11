from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    data_dir: Path = Path("../data")
    mineru_command: str = "mineru"
    mineru_parse_method: str = "auto"
    worker_poll_seconds: float = 1.0
    max_workers: int = 1
    mineru_timeout_seconds: int = 3600
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_embedding: bool = True
    enable_formula_enhancer: bool = True
    ai_provider: str = "openai-compatible"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.2
    ai_max_tokens: int = 2048
    render_command: str = ""
    render_dpi: int = 144
    retrieval_top_k: int = 8
    retrieval_context_chars: int = 24000
    cpu_only: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def documents_dir(self): return self.data_dir / "documents"

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.documents_dir.mkdir(parents=True, exist_ok=True)
