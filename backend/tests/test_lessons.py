import pytest
from sqlalchemy.exc import IntegrityError


def _auth_headers(client, username: str = "teacher_lessons") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Lesson Teacher",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _generate_payload(**overrides):
    payload = {
        "subject": "Writing",
        "chapter": "Lesson format",
        "stage": "Graduate exam",
        "duration_minutes": 45,
        "student_level": "Basic",
        "teaching_goal": "Master lesson format",
        "use_materials": False,
        "material_ids": [],
    }
    payload.update(overrides)
    return payload


def _save_payload(**overrides):
    payload = {
        "title": "Lesson format class",
        "subject": "Writing",
        "chapter": "Lesson format",
        "stage": "Graduate exam",
        "duration_minutes": 45,
        "student_level": "Basic",
        "content": "Teaching goal: master lesson format.",
    }
    payload.update(overrides)
    return payload


def _upload_txt(client, headers: dict[str, str], title: str, content: str):
    return client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": title},
        files={"file": ("lesson.txt", content.encode("utf-8"), "text/plain")},
    )


def test_generate_lesson_without_materials_returns_content_status_and_compliance(client):
    headers = _auth_headers(client)

    response = client.post(
        "/api/lessons/generate",
        headers=headers,
        json=_generate_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert "Master lesson format" in body["content"]
    assert body["references"] == []
    assert body["provider_status"]["provider"] == "mock"
    assert body["compliance"]["risk_level"] == "low"


def test_save_generated_lesson_creates_lesson_and_version_one(client):
    headers = _auth_headers(client, username="teacher_save_lesson")

    create_response = client.post(
        "/api/lessons",
        headers=headers,
        json=_save_payload(),
    )

    assert create_response.status_code == 201
    lesson = create_response.json()
    assert lesson["id"]
    assert lesson["title"] == "Lesson format class"
    assert lesson["current_content"] == "Teaching goal: master lesson format."
    assert lesson["compliance_level"] == "low"

    versions_response = client.get(
        f"/api/lessons/{lesson['id']}/versions",
        headers=headers,
    )

    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1
    assert versions[0]["content"] == lesson["current_content"]


def test_restore_lesson_version_updates_current_content_and_preserves_history(client):
    headers = _auth_headers(client, username="teacher_restore_lesson")
    create_response = client.post(
        "/api/lessons",
        headers=headers,
        json=_save_payload(content="First version content"),
    )
    lesson_id = create_response.json()["id"]
    version_id = client.get(
        f"/api/lessons/{lesson_id}/versions",
        headers=headers,
    ).json()[0]["id"]

    restore_response = client.post(
        f"/api/lessons/{lesson_id}/restore-version",
        headers=headers,
        json={"version_id": version_id},
    )

    assert restore_response.status_code == 200
    restored = restore_response.json()
    assert restored["current_content"] == "First version content"

    versions_response = client.get(
        f"/api/lessons/{lesson_id}/versions",
        headers=headers,
    )
    versions = versions_response.json()
    assert [version["version_no"] for version in versions] == [1, 2]
    assert versions[1]["content"] == "First version content"
    assert versions[1]["change_note"].endswith(" 1")


def test_duplicate_version_numbers_are_rejected_by_database(client):
    from app.core.database import get_session_local
    from app.lessons.models import LessonVersion

    headers = _auth_headers(client, username="teacher_duplicate_version")
    lesson_id = client.post(
        "/api/lessons",
        headers=headers,
        json=_save_payload(title="Duplicate Version Lesson"),
    ).json()["id"]

    session_local = get_session_local()
    with session_local() as db:
        db.add(
            LessonVersion(
                lesson_id=lesson_id,
                version_no=1,
                content="duplicate content",
                change_note="duplicate",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_cross_user_cannot_get_lesson_or_versions(client):
    owner_headers = _auth_headers(client, username="teacher_owner_lesson")
    other_headers = _auth_headers(client, username="teacher_other_lesson")
    lesson_id = client.post(
        "/api/lessons",
        headers=owner_headers,
        json=_save_payload(title="Owner Lesson"),
    ).json()["id"]

    lesson_response = client.get(f"/api/lessons/{lesson_id}", headers=other_headers)
    versions_response = client.get(
        f"/api/lessons/{lesson_id}/versions",
        headers=other_headers,
    )

    assert lesson_response.status_code == 404
    assert versions_response.status_code == 404


def test_list_lessons_returns_only_current_user_lessons(client):
    owner_headers = _auth_headers(client, username="teacher_list_owner")
    other_headers = _auth_headers(client, username="teacher_list_other")
    client.post(
        "/api/lessons",
        headers=owner_headers,
        json=_save_payload(title="Owner Lesson"),
    )
    client.post(
        "/api/lessons",
        headers=other_headers,
        json=_save_payload(title="Other Lesson"),
    )

    response = client.get("/api/lessons", headers=owner_headers)

    assert response.status_code == 200
    lessons = response.json()
    assert [lesson["title"] for lesson in lessons] == ["Owner Lesson"]


def test_generate_with_materials_returns_owner_scoped_reference_metadata(client):
    owner_headers = _auth_headers(client, username="teacher_material_lesson")
    other_headers = _auth_headers(client, username="teacher_material_other")
    owner_material = _upload_txt(
        client,
        owner_headers,
        "Owner Format",
        "lesson format includes greeting body closing",
    ).json()
    other_material = _upload_txt(
        client,
        other_headers,
        "Other Format",
        "lesson format other user private content",
    ).json()

    response = client.post(
        "/api/lessons/generate",
        headers=owner_headers,
        json=_generate_payload(
            chapter="lesson format",
            teaching_goal="includes",
            use_materials=True,
            material_ids=[owner_material["id"], other_material["id"]],
        ),
    )

    assert response.status_code == 200
    references = response.json()["references"]
    assert references
    assert any(
        reference["material_id"] == owner_material["id"]
        and "greeting body closing" in reference["content"]
        for reference in references
    )
    assert all("id" in reference for reference in references)
    assert all("page_no" in reference for reference in references)
    assert all("slide_no" in reference for reference in references)
    assert all("score" in reference for reference in references)
    assert all(reference["material_id"] != other_material["id"] for reference in references)


def test_phase2_generate_lesson_returns_multi_ai_review(client, monkeypatch):
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    headers = _auth_headers(client, username="teacher_lesson_review")

    response = client.post(
        "/api/lessons/generate",
        headers=headers,
        json=_generate_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["enabled"] is True
    assert body["review"]["status"] in {"passed", "warning"}
    assert body["review"]["reviewer_model"]
    assert "warnings" in body["review"]
    assert "suggestions" in body["review"]
    assert "raw_review" in body["review"]


def test_generate_lesson_can_enable_review_per_request_when_global_disabled(client, monkeypatch):
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    headers = _auth_headers(client, username="teacher_lesson_request_review")

    response = client.post(
        "/api/lessons/generate",
        headers=headers,
        json=_generate_payload(multi_agent_review=True, auto_revise=True),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["enabled"] is True
    assert body["review"]["status"] in {"passed", "warning"}
    assert body["review"]["reviewer_model"]
