def _auth_headers(client, username: str = "teacher_courses") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Course Teacher",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_course(client, headers: dict[str, str], **overrides):
    payload = {
        "title": "Phase 3 English Course",
        "subject": "English",
        "exam_type": "zhongkao",
        "description": "Course system baseline for phase 3.",
        "status": "active",
    }
    payload.update(overrides)
    return client.post("/api/courses", headers=headers, json=payload)


def _create_chapter(client, headers: dict[str, str], course_id: int, **overrides):
    payload = {
        "title": "Unit 1 Foundations",
        "summary": "Foundational course chapter.",
        "order_index": 1,
    }
    payload.update(overrides)
    return client.post(
        f"/api/courses/{course_id}/chapters",
        headers=headers,
        json=payload,
    )


def test_course_hierarchy_crud_and_detail(client):
    headers = _auth_headers(client, username="teacher_course_hierarchy")
    course_response = _create_course(client, headers)
    assert course_response.status_code == 201
    course = course_response.json()

    chapter_response = _create_chapter(client, headers, course["id"])
    assert chapter_response.status_code == 201
    chapter = chapter_response.json()

    session_response = client.post(
        f"/api/chapters/{chapter['id']}/sessions",
        headers=headers,
        json={
            "title": "Session 1 Course Overview",
            "duration_minutes": 45,
            "teaching_goal": "Understand course expectations.",
            "order_index": 1,
            "lesson_id": None,
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["course_id"] == course["id"]

    knowledge_point_response = client.post(
        f"/api/courses/{course['id']}/knowledge-points",
        headers=headers,
        json={
            "chapter_id": chapter["id"],
            "session_id": session["id"],
            "name": "Key vocabulary",
            "description": "Core vocabulary for the first unit.",
            "difficulty": "basic",
        },
    )
    assert knowledge_point_response.status_code == 201
    knowledge_point = knowledge_point_response.json()

    detail_response = client.get(f"/api/courses/{course['id']}", headers=headers)

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == course["id"]
    assert detail["chapters"][0]["id"] == chapter["id"]
    assert detail["chapters"][0]["title"] == "Unit 1 Foundations"
    assert detail["chapters"][0]["sessions"][0]["id"] == session["id"]
    assert detail["chapters"][0]["sessions"][0]["course_id"] == course["id"]
    assert detail["chapters"][0]["sessions"][0]["title"] == "Session 1 Course Overview"
    assert detail["knowledge_points"][0]["id"] == knowledge_point["id"]
    assert detail["knowledge_points"][0]["name"] == "Key vocabulary"


def test_course_list_and_cross_user_scope(client):
    owner_headers = _auth_headers(client, username="teacher_course_owner")
    other_headers = _auth_headers(client, username="teacher_course_other")
    owner_course = _create_course(
        client,
        owner_headers,
        title="Owner Course",
    )
    assert owner_course.status_code == 201
    other_course = _create_course(
        client,
        other_headers,
        title="Other Course",
    )
    assert other_course.status_code == 201
    owner_course = owner_course.json()

    list_response = client.get("/api/courses", headers=owner_headers)
    other_detail_response = client.get(
        f"/api/courses/{owner_course['id']}",
        headers=other_headers,
    )

    assert list_response.status_code == 200
    courses = list_response.json()
    assert [course["title"] for course in courses] == ["Owner Course"]
    assert other_detail_response.status_code == 404


def test_course_archive_instead_of_hard_delete(client):
    headers = _auth_headers(client, username="teacher_course_archive")
    course_response = _create_course(client, headers, title="Archive Course")
    assert course_response.status_code == 201
    course = course_response.json()

    delete_response = client.delete(f"/api/courses/{course['id']}", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "archived"


def test_course_patch_and_status_validation(client):
    headers = _auth_headers(client, username="teacher_course_patch")
    course_response = _create_course(client, headers, title="Patch Course", status="draft")
    assert course_response.status_code == 201
    course = course_response.json()

    patch_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=headers,
        json={"title": "Updated Course", "status": "active"},
    )
    invalid_status_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=headers,
        json={"status": "unknown"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Course"
    assert patch_response.json()["status"] == "active"
    assert invalid_status_response.status_code == 422


def test_course_patch_rejects_null_non_nullable_fields(client):
    headers = _auth_headers(client, username="teacher_course_patch_nulls")
    course_response = _create_course(
        client,
        headers,
        title="Stable Course",
        status="draft",
    )
    assert course_response.status_code == 201
    course = course_response.json()

    null_title_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=headers,
        json={"title": None},
    )
    null_status_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=headers,
        json={"status": None},
    )
    detail_response = client.get(f"/api/courses/{course['id']}", headers=headers)

    assert null_title_response.status_code == 422
    assert null_status_response.status_code == 422
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Stable Course"
    assert detail_response.json()["status"] == "draft"


def test_knowledge_point_invalid_difficulty_defaults_to_basic(client):
    headers = _auth_headers(client, username="teacher_course_difficulty")
    course_response = _create_course(client, headers)
    assert course_response.status_code == 201
    course = course_response.json()

    knowledge_point_response = client.post(
        f"/api/courses/{course['id']}/knowledge-points",
        headers=headers,
        json={
            "name": "Normalized difficulty",
            "description": "Invalid difficulty should use the baseline value.",
            "difficulty": "expert",
        },
    )

    assert knowledge_point_response.status_code == 201
    assert knowledge_point_response.json()["difficulty"] == "basic"


def test_cross_user_chapter_session_and_knowledge_point_scope(client):
    owner_headers = _auth_headers(client, username="teacher_course_nested_owner")
    other_headers = _auth_headers(client, username="teacher_course_nested_other")
    owner_course_response = _create_course(client, owner_headers, title="Nested Owner")
    assert owner_course_response.status_code == 201
    owner_course = owner_course_response.json()
    chapter_response = _create_chapter(client, owner_headers, owner_course["id"])
    assert chapter_response.status_code == 201
    owner_chapter = chapter_response.json()

    other_session_response = client.post(
        f"/api/chapters/{owner_chapter['id']}/sessions",
        headers=other_headers,
        json={
            "title": "Forbidden Session",
            "duration_minutes": 45,
            "teaching_goal": "Should not be created.",
            "order_index": 1,
            "lesson_id": None,
        },
    )
    other_knowledge_point_response = client.post(
        f"/api/courses/{owner_course['id']}/knowledge-points",
        headers=other_headers,
        json={
            "chapter_id": owner_chapter["id"],
            "name": "Forbidden KP",
            "description": "Should not be created.",
            "difficulty": "basic",
        },
    )

    assert other_session_response.status_code == 404
    assert other_knowledge_point_response.status_code == 404


def test_course_hierarchy_uses_chapters_table(client):
    from sqlalchemy import inspect

    from app.core.database import get_engine

    table_names = inspect(get_engine()).get_table_names()

    assert "chapters" in table_names
    assert "course_chapters" not in table_names


def test_sqlite_course_hierarchy_compatibility_migration(tmp_path, monkeypatch):
    import sqlite3

    from sqlalchemy import inspect, text

    from app.core.config import get_settings
    from app.core.database import clear_database_caches, get_engine, init_db
    from app.courses import models as course_models  # noqa: F401

    db_path = tmp_path / "legacy_courses.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                subject VARCHAR(128) NOT NULL,
                exam_type VARCHAR(128) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(32) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            CREATE TABLE course_chapters (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                summary TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            CREATE TABLE lesson_sessions (
                id INTEGER PRIMARY KEY,
                chapter_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                duration_minutes INTEGER NOT NULL,
                teaching_goal TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            INSERT INTO courses VALUES (
                10, 1, 'Legacy Course', 'English', 'zhongkao', '', 'active',
                '2026-01-01 00:00:00', '2026-01-01 00:00:00'
            );
            INSERT INTO course_chapters VALUES (
                20, 10, 'Legacy Chapter', '', 1,
                '2026-01-01 00:00:00', '2026-01-01 00:00:00'
            );
            INSERT INTO lesson_sessions VALUES (
                30, 20, 'Legacy Session', 45, '', 1,
                '2026-01-01 00:00:00', '2026-01-01 00:00:00'
            );
            """
        )

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    clear_database_caches()

    try:
        init_db()
        engine = get_engine()
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        session_columns = {
            column["name"] for column in inspector.get_columns("lesson_sessions")
        }

        with engine.connect() as connection:
            backfilled_course_id = connection.execute(
                text("SELECT course_id FROM lesson_sessions WHERE id = 30")
            ).scalar_one()

        assert "chapters" in table_names
        assert "course_chapters" not in table_names
        assert "course_id" in session_columns
        assert backfilled_course_id == 10
    finally:
        get_settings.cache_clear()
        clear_database_caches()
