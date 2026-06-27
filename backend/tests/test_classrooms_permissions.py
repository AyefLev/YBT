def _auth_headers(client, username: str, role: str = "teacher") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": username.replace("_", " ").title(),
            "role": role,
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client, username: str = "admin_permissions") -> dict[str, str]:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.core.database import get_session_local

    headers = _auth_headers(client, username=username)
    session_local = get_session_local()
    with session_local() as db:
        user = db.scalar(select(User).where(User.username == username))
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        user.roles = [admin_role]
        db.commit()
    return headers


def test_student_registration_gets_student_permissions(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "student_one",
            "email": "student_one@example.com",
            "password": "secret-password",
            "display_name": "Student One",
            "role": "student",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["roles"] == ["student"]
    assert body["requested_role"] == "student"
    assert body["account_status"] == "approved"
    assert set(body["permissions"]) == {"class:join", "assignment:submit"}


def test_teacher_application_can_be_approved_by_admin(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "pending_teacher",
            "email": "pending_teacher@example.com",
            "password": "secret-password",
            "display_name": "Pending Teacher",
            "role": "teacher",
            "apply_for_teacher_review": True,
            "application_note": "I teach English.",
        },
    )
    admin_headers = _admin_headers(client, username="admin_teacher_review")

    assert register_response.status_code == 201
    pending = register_response.json()
    assert pending["roles"] == ["pending_teacher"]
    assert pending["account_status"] == "pending"

    approve_response = client.post(
        f"/api/admin/teacher-applications/{pending['id']}/approve",
        headers=admin_headers,
        json={"note": "verified"},
    )

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["roles"] == ["teacher"]
    assert approved["account_status"] == "approved"
    assert "class:manage" in approved["permissions"]


def test_admin_can_create_update_and_deactivate_user(client):
    admin_headers = _admin_headers(client, username="admin_user_crud")

    create_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "created_student",
            "email": "created_student@example.com",
            "password": "secret-password",
            "display_name": "Created Student",
            "roles": ["student"],
            "requested_role": "student",
        },
    )
    user_id = create_response.json()["id"]
    update_response = client.patch(
        f"/api/admin/users/{user_id}",
        headers=admin_headers,
        json={"display_name": "Updated Student"},
    )
    delete_response = client.delete(f"/api/admin/users/{user_id}", headers=admin_headers)

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Updated Student"
    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False


def test_teacher_classroom_student_assignment_flow(client):
    teacher_headers = _auth_headers(client, username="teacher_classroom")
    student_headers = _auth_headers(client, username="student_classroom", role="student")

    class_response = client.post(
        "/api/classrooms",
        headers=teacher_headers,
        json={"name": "English Class 1", "description": "Writing practice"},
    )
    classroom = class_response.json()
    join_response = client.post(
        "/api/classrooms/join",
        headers=student_headers,
        json={"invite_code": classroom["invite_code"]},
    )
    students_response = client.get(
        f"/api/classrooms/{classroom['id']}/students",
        headers=teacher_headers,
    )
    assignment_response = client.post(
        f"/api/classrooms/{classroom['id']}/assignments",
        headers=teacher_headers,
        json={
            "title": "Letter homework",
            "description": "Finish one letter.",
            "instructions": "Write a suggestion letter.",
        },
    )
    assignment = assignment_response.json()
    my_assignments_response = client.get("/api/assignments/my", headers=student_headers)
    submit_response = client.post(
        f"/api/assignments/{assignment['id']}/submit",
        headers=student_headers,
        json={"content": "Dear Sir or Madam, ..."},
    )
    submissions_response = client.get(
        f"/api/assignments/{assignment['id']}/submissions",
        headers=teacher_headers,
    )
    submission = submissions_response.json()[0]
    grade_response = client.post(
        f"/api/submissions/{submission['id']}/grade",
        headers=teacher_headers,
        json={"score": 92, "feedback": "Clear structure."},
    )

    assert class_response.status_code == 201
    assert join_response.status_code == 200
    assert students_response.status_code == 200
    assert students_response.json()[0]["username"] == "student_classroom"
    assert assignment_response.status_code == 201
    assert my_assignments_response.status_code == 200
    assert my_assignments_response.json()[0]["id"] == assignment["id"]
    assert submit_response.status_code == 200
    assert submissions_response.status_code == 200
    assert grade_response.status_code == 200
    assert grade_response.json()["score"] == 92
    assert grade_response.json()["status"] == "graded"


def test_teacher_cannot_manage_other_teacher_classroom(client):
    owner_headers = _auth_headers(client, username="teacher_class_owner")
    other_headers = _auth_headers(client, username="teacher_class_other")

    class_response = client.post(
        "/api/classrooms",
        headers=owner_headers,
        json={"name": "Private Class"},
    )
    classroom_id = class_response.json()["id"]

    students_response = client.get(
        f"/api/classrooms/{classroom_id}/students",
        headers=other_headers,
    )
    assignment_response = client.post(
        f"/api/classrooms/{classroom_id}/assignments",
        headers=other_headers,
        json={"title": "Forbidden"},
    )

    assert students_response.status_code == 404
    assert assignment_response.status_code == 404
