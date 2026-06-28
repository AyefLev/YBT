from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.embeddings import DEFAULT_EMBEDDING_DIMENSIONS, DEFAULT_EMBEDDING_MODEL

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "yanbeitong-ai"
    database_url: str = "sqlite:///../data/app.db"
    redis_url: str = ""
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440
    admin_bootstrap_username: str = ""
    admin_bootstrap_email: str = ""
    admin_bootstrap_password: str = ""
    admin_bootstrap_display_name: str = "System Admin"
    llm_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    llm_api_key: str = ""
    llm_model: str = "mimo-v2.5-pro"
    llm_generate_model: str = ""
    llm_review_model: str = ""
    llm_revise_model: str = ""
    generate_llm_base_url: str = ""
    generate_llm_api_key: str = ""
    review_llm_base_url: str = ""
    review_llm_api_key: str = ""
    revise_llm_base_url: str = ""
    revise_llm_api_key: str = ""
    llm_multi_agent_review: bool = False
    llm_timeout_seconds: int = 120
    llm_mock_on_failure: bool = False
    vision_llm_base_url: str = ""
    vision_llm_api_key: str = ""
    vision_llm_model: str = ""
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS
    vector_store_provider: str = "disabled"
    qdrant_url: str = ""
    qdrant_collection: str = "yanbeitong_material_chunks"
    qdrant_timeout_seconds: float = 2.0
    task_queue_mode: str = "inline"
    task_queue_prefix: str = "ybt:tasks"
    task_worker_queues: str = "materials,exports,presentations"
    task_worker_poll_seconds: int = 5
    material_parse_wait_seconds: float = 2.0
    upload_dir: Path = Path("../data/uploads")
    export_dir: Path = Path("../data/exports")

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
    )

    def validate_jwt_secret(self) -> None:
        unsafe_values = {
            "",
            "change-me-in-local-env",
            "replace-with-a-long-random-secret",
        }
        if self.jwt_secret in unsafe_values or len(self.jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET must be set to a non-placeholder value at least 32 characters long."
            )


def _normalize_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (BACKEND_DIR / path).resolve()


def _normalize_sqlite_url(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return database_url

    database_path = database_url.removeprefix(prefix)
    if database_path == ":memory:":
        return database_url

    path = Path(database_path)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    return f"{prefix}{path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_url = _normalize_sqlite_url(settings.database_url)
    settings.upload_dir = _normalize_path(settings.upload_dir)
    settings.export_dir = _normalize_path(settings.export_dir)
    settings.llm_generate_model = settings.llm_generate_model or settings.llm_model
    settings.llm_review_model = settings.llm_review_model or settings.llm_model
    settings.llm_revise_model = settings.llm_revise_model or settings.llm_model
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings
