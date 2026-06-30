def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "yanbeitong-ai"}


def test_root_returns_service_links(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "yanbeitong-ai"
    assert body["health"] == "/api/health"
    assert body["docs"] == "/docs"


def test_create_app_uses_current_settings(monkeypatch, tmp_path):
    from app.core.database import clear_database_caches
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-enough-length")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    get_settings.cache_clear()
    clear_database_caches()

    response = client_response(create_app())

    assert response.json() == {"status": "ok", "app": "test-app"}
    clear_database_caches()


def test_create_app_applies_configured_cors_origins(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.core.database import clear_database_caches
    from app.main import create_app

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cors.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-enough-length")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://tauri.localhost,https://school.example.edu")
    get_settings.cache_clear()
    clear_database_caches()

    with TestClient(create_app()) as test_client:
        response = test_client.options(
            "/api/health",
            headers={
                "Origin": "http://tauri.localhost",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"
    clear_database_caches()


def test_settings_normalizes_paths_from_backend_dir(monkeypatch):
    from app.core.config import BACKEND_DIR, get_settings

    monkeypatch.setenv("DATABASE_URL", "sqlite:///../data/app.db")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("UPLOAD_DIR", "../data/uploads")
    monkeypatch.setenv("EXPORT_DIR", "../data/exports")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.upload_dir == (BACKEND_DIR / "../data/uploads").resolve()
    assert settings.export_dir == (BACKEND_DIR / "../data/exports").resolve()
    assert settings.database_url.endswith("/data/app.db")
    assert settings.jwt_secret == ""


def test_database_helpers_are_lazy_and_sqlite_specific(monkeypatch):
    from app.core import database

    database.clear_database_caches()
    calls = []

    def fake_create_engine(url, **kwargs):
        calls.append((url, kwargs))
        return object()

    monkeypatch.setattr(database, "create_engine", fake_create_engine)

    sqlite_engine = database.get_engine("sqlite:///test.db")
    postgres_engine = database.get_engine("postgresql://user:pass@example.com/db")

    assert sqlite_engine is not postgres_engine
    assert calls[0] == ("sqlite:///test.db", {"connect_args": {"check_same_thread": False}})
    assert calls[1] == ("postgresql://user:pass@example.com/db", {})


def test_database_default_cache_uses_resolved_database_url(monkeypatch, tmp_path):
    from app.core import database
    from app.core.config import get_settings

    database.clear_database_caches()
    urls = []

    def fake_create_engine(url, **kwargs):
        urls.append(url)
        return object()

    monkeypatch.setattr(database, "create_engine", fake_create_engine)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'first.db'}")
    get_settings.cache_clear()
    first_engine = database.get_engine()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'second.db'}")
    get_settings.cache_clear()
    second_engine = database.get_engine()

    assert first_engine is not second_engine
    assert urls == [
        f"sqlite:///{(tmp_path / 'first.db').as_posix()}",
        f"sqlite:///{(tmp_path / 'second.db').as_posix()}",
    ]

    database.clear_database_caches()


def test_init_db_adds_is_active_to_existing_sqlite_users_table(monkeypatch, tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.auth import models as auth_models  # noqa: F401
    from app.core.config import get_settings
    from app.core.database import clear_database_caches, init_db

    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(64) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    display_name VARCHAR(128) NOT NULL
                )
                """
            )
        )
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    clear_database_caches()

    init_db()

    migrated_engine = create_engine(database_url)
    columns = {column["name"] for column in inspect(migrated_engine).get_columns("users")}
    migrated_engine.dispose()

    assert "is_active" in columns
    clear_database_caches()


def client_response(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        return test_client.get("/api/health")
