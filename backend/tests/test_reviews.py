def _auth_headers(client, username: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": username,
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _manager_headers(client, username: str = "manager_review") -> dict[str, str]:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.core.database import get_session_local

    headers = _auth_headers(client, username)
    session_local = get_session_local()
    with session_local() as db:
        user = db.scalar(select(User).where(User.username == username))
        manager_role = db.scalar(select(Role).where(Role.name == "teaching_manager"))
        assert user is not None
        assert manager_role is not None
        user.roles = [manager_role]
        db.commit()
    return headers


def _create_question(client, headers: dict[str, str]):
    response = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "Review Question",
            "subject": "English",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "Explain letter format.",
            "options": [],
            "answer": "Greeting, body, closing.",
            "analysis": "Basic writing format.",
            "tags": [],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_lesson(client, headers: dict[str, str]):
    response = client.post(
        "/api/lessons",
        headers=headers,
        json={
            "title": "Review Lesson",
            "subject": "English",
            "chapter": "Letter writing",
            "stage": "practice",
            "duration_minutes": 45,
            "student_level": "basic",
            "content": "Lesson plan content for review.",
            "change_note": "initial",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_teacher_submits_question_and_manager_approves(client):
    teacher_headers = _auth_headers(client, "teacher_review_question")
    manager_headers = _manager_headers(client, "manager_review_question")
    question = _create_question(client, teacher_headers)

    submit = client.post(
        f"/api/questions/{question['id']}/submit-review",
        headers=teacher_headers,
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "pending_review"

    pending = client.get("/api/reviews/pending", headers=manager_headers)
    assert pending.status_code == 200
    pending_question = next(
        item
        for item in pending.json()
        if item["resource_type"] == "question"
        and item["resource_id"] == question["id"]
    )
    assert pending_question["owner_username"] == "teacher_review_question"
    assert pending_question["detail"]["stem"] == "Explain letter format."
    assert pending_question["detail"]["answer"] == "Greeting, body, closing."
    assert pending_question["detail"]["analysis"] == "Basic writing format."

    approve = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=manager_headers,
        json={"comment": "Approved for class use."},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["review_comment"] == "Approved for class use."


def test_review_permission_and_invalid_transition(client):
    teacher_headers = _auth_headers(client, "teacher_review_denied")
    question = _create_question(client, teacher_headers)

    approve_without_permission = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=teacher_headers,
        json={"comment": "Should fail"},
    )
    assert approve_without_permission.status_code == 403

    manager_headers = _manager_headers(client, "manager_invalid_transition")
    invalid_approve = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=manager_headers,
        json={"comment": "Not submitted yet"},
    )
    assert invalid_approve.status_code == 400


def test_rejected_question_can_return_to_draft(client):
    teacher_headers = _auth_headers(client, "teacher_review_return_draft")
    manager_headers = _manager_headers(client, "manager_review_return_draft")
    question = _create_question(client, teacher_headers)

    submit = client.post(
        f"/api/questions/{question['id']}/submit-review",
        headers=teacher_headers,
    )
    assert submit.status_code == 200
    reject = client.post(
        f"/api/reviews/question/{question['id']}/reject",
        headers=manager_headers,
        json={"comment": "Needs revision."},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    returned = client.post(
        f"/api/reviews/question/{question['id']}/return-draft",
        headers=teacher_headers,
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "draft"
    assert returned.json()["review_comment"] == ""


def test_teacher_submits_lesson_and_manager_rejects(client):
    teacher_headers = _auth_headers(client, "teacher_review_lesson")
    manager_headers = _manager_headers(client, "manager_review_lesson")
    lesson = _create_lesson(client, teacher_headers)

    submit = client.post(
        f"/api/lessons/{lesson['id']}/submit-review",
        headers=teacher_headers,
    )
    assert submit.status_code == 200
    assert submit.json()["review_status"] == "pending_review"

    pending = client.get("/api/reviews/pending", headers=manager_headers)
    assert pending.status_code == 200
    pending_lesson = next(
        item
        for item in pending.json()
        if item["resource_type"] == "lesson"
        and item["resource_id"] == lesson["id"]
    )
    assert pending_lesson["owner_username"] == "teacher_review_lesson"
    assert pending_lesson["detail"]["content"] == "Lesson plan content for review."
    assert pending_lesson["detail"]["duration_minutes"] == 45

    reject = client.post(
        f"/api/reviews/lesson/{lesson['id']}/reject",
        headers=manager_headers,
        json={"comment": "Add clearer classroom steps."},
    )
    assert reject.status_code == 200
    assert reject.json()["review_status"] == "rejected"
    assert reject.json()["review_comment"] == "Add clearer classroom steps."
