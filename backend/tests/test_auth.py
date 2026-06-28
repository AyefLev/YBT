import jwt


def test_seed_default_auth_data_does_not_overwrite_existing_role_permissions(client):
    from sqlalchemy import select

    from app.auth.models import Role
    from app.auth.service import seed_default_auth_data
    from app.core.database import get_session_local

    session_local = get_session_local()
    with session_local() as db:
        teaching_manager = db.scalar(select(Role).where(Role.name == "teaching_manager"))
        teaching_manager.permissions = [
            permission
            for permission in teaching_manager.permissions
            if permission.code != "log:view"
        ]
        expected_permissions = sorted(
            permission.code for permission in teaching_manager.permissions
        )
        db.commit()

    with session_local() as db:
        seed_default_auth_data(db)

    with session_local() as db:
        teaching_manager = db.scalar(select(Role).where(Role.name == "teaching_manager"))
        permission_codes = sorted(
            permission.code for permission in teaching_manager.permissions
        )

    assert "log:view" not in permission_codes
    assert permission_codes == expected_permissions


def test_register_user_recreates_missing_teacher_role_with_default_permissions(client):
    from sqlalchemy import select

    from app.auth.models import Role
    from app.auth.schemas import UserRegister
    from app.auth.service import register_user
    from app.core.database import get_session_local

    session_local = get_session_local()
    with session_local() as db:
        teacher_role = db.scalar(select(Role).where(Role.name == "teacher"))
        db.delete(teacher_role)
        db.commit()

    with session_local() as db:
        user = register_user(
            db,
            UserRegister(
                username="reseeded_teacher",
                email="reseeded_teacher@example.com",
                password="secret-password",
                display_name="Reseeded Teacher",
            ),
        )
        permission_codes = user.permission_codes

    assert user.role_names == ["teacher"]
    assert {
        "lesson:create",
        "lesson:export",
        "exercise:create",
        "material:upload",
        "course:create",
        "class:manage",
        "assignment:manage",
        "assignment:grade",
    }.issubset(set(permission_codes))


def test_bootstrap_admin_env_creates_admin_user_with_management_access(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.core.database import clear_database_caches
    from app.main import create_app

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'bootstrap.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-enough-length")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USERNAME", "bootstrap_admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAIL", "bootstrap_admin@example.com")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "bootstrap-password")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_DISPLAY_NAME", "Bootstrap Admin")
    get_settings.cache_clear()
    clear_database_caches()

    with TestClient(create_app()) as test_client:
        login_response = test_client.post(
            "/api/auth/login",
            json={"username": "bootstrap_admin", "password": "bootstrap-password"},
        )
        assert login_response.status_code == 200
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        me_response = test_client.get("/api/auth/me", headers=headers)
        roles_response = test_client.get("/api/admin/roles", headers=headers)
        logs_response = test_client.get("/api/logs/operations", headers=headers)

    assert me_response.status_code == 200
    assert "admin" in me_response.json()["roles"]
    assert "admin:user_manage" in me_response.json()["permissions"]
    assert "lesson:view_all" not in me_response.json()["permissions"]
    assert "material:upload" not in me_response.json()["permissions"]
    assert roles_response.status_code == 200
    assert logs_response.status_code == 200

    get_settings.cache_clear()
    clear_database_caches()


def test_register_login_and_me_returns_default_teacher_permissions(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "teacher1",
            "email": "teacher1@example.com",
            "password": "secret-password",
            "display_name": "Teacher One",
        },
    )

    assert register_response.status_code == 201
    registered_user = register_response.json()
    assert registered_user["username"] == "teacher1"
    assert registered_user["email"] == "teacher1@example.com"
    assert registered_user["display_name"] == "Teacher One"
    assert registered_user["is_active"] is True
    assert registered_user["roles"] == ["teacher"]
    assert "password" not in registered_user

    login_response = client.post(
        "/api/auth/login",
        json={"username": "teacher1", "password": "secret-password"},
    )

    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert token_payload["token_type"] == "bearer"
    assert token_payload["access_token"]

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )

    assert me_response.status_code == 200
    current_user = me_response.json()
    assert current_user["id"] == registered_user["id"]
    assert current_user["username"] == "teacher1"
    assert current_user["email"] == "teacher1@example.com"
    assert current_user["display_name"] == "Teacher One"
    assert current_user["is_active"] is True
    assert current_user["roles"] == ["teacher"]
    assert {
        "lesson:create",
        "lesson:export",
        "exercise:create",
        "material:upload",
        "course:create",
        "class:manage",
        "assignment:manage",
        "assignment:grade",
    }.issubset(set(current_user["permissions"]))


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "teacher2",
            "email": "teacher2@example.com",
            "password": "secret-password",
            "display_name": "Teacher Two",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"username": "teacher2", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_rejects_token_without_exp(client):
    from app.core.config import get_settings
    from app.core.security import ALGORITHM

    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "teacher3",
            "email": "teacher3@example.com",
            "password": "secret-password",
            "display_name": "Teacher Three",
        },
    )
    user_id = register_response.json()["id"]
    token = jwt.encode({"sub": str(user_id)}, get_settings().jwt_secret, algorithm=ALGORITHM)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_inactive_user_cannot_login_or_use_existing_token(client):
    from app.auth.models import User
    from app.core.database import get_session_local

    client.post(
        "/api/auth/register",
        json={
            "username": "teacher4",
            "email": "teacher4@example.com",
            "password": "secret-password",
            "display_name": "Teacher Four",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": "teacher4", "password": "secret-password"},
    )
    token = login_response.json()["access_token"]

    session_local = get_session_local()
    with session_local() as db:
        user = db.query(User).filter(User.username == "teacher4").one()
        user.is_active = False
        db.commit()

    inactive_login_response = client.post(
        "/api/auth/login",
        json={"username": "teacher4", "password": "secret-password"},
    )
    inactive_me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert inactive_login_response.status_code == 401
    assert inactive_me_response.status_code == 401


def test_token_creation_rejects_unsafe_jwt_secret(monkeypatch):
    import pytest

    from app.core.config import get_settings
    from app.core.security import create_access_token

    for unsafe_secret in ("", "change-me-in-local-env", "replace-with-a-long-random-secret"):
        monkeypatch.setenv("JWT_SECRET", unsafe_secret)
        get_settings.cache_clear()

        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            create_access_token("1")

    get_settings.cache_clear()


def test_app_startup_rejects_unsafe_jwt_secret(monkeypatch, tmp_path):
    import pytest
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.core.database import clear_database_caches
    from app.main import create_app

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("JWT_SECRET", "replace-with-a-long-random-secret")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))
    get_settings.cache_clear()
    clear_database_caches()

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(create_app()):
            pass

    get_settings.cache_clear()
    clear_database_caches()
