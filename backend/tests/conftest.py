from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(monkeypatch, tmp_path):
    from app.core.config import get_settings
    from app.core.database import clear_database_caches, init_db
    from app.main import create_app
    from app.cache.client import clear_cache_backend

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-enough-length")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "true")
    monkeypatch.setenv("TASK_QUEUE_MODE", "inline")
    monkeypatch.setenv("MATERIAL_PARSE_WAIT_SECONDS", "2")
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "disabled")
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    get_settings.cache_clear()
    clear_database_caches()
    clear_cache_backend()

    test_app = create_app()
    init_db()

    with TestClient(test_app) as c:
        yield c

    get_settings.cache_clear()
    clear_database_caches()
    clear_cache_backend()
