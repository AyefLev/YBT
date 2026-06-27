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


def _role_headers(client, username: str, role_name: str) -> dict[str, str]:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.core.database import get_session_local

    headers = _auth_headers(client, username=username)
    session_local = get_session_local()
    with session_local() as db:
        user = db.scalar(select(User).where(User.username == username))
        role = db.scalar(select(Role).where(Role.name == role_name))
        user.roles = [role]
        db.commit()
    return headers


def _create_course(client, headers: dict[str, str], title: str):
    response = client.post(
        "/api/courses",
        headers=headers,
        json={
            "title": title,
            "subject": "Math",
            "exam_type": "postgraduate",
            "description": "Scoped course",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_classroom(client, headers: dict[str, str], name: str):
    response = client.post(
        "/api/classrooms",
        headers=headers,
        json={"name": name, "description": "Scoped classroom"},
    )
    assert response.status_code == 201
    return response.json()


def test_admin_can_view_teacher_assets_with_owner_labels_but_cannot_teach_in_them(client):
    teacher_headers = _auth_headers(client, "teacher_scope_owner")
    admin_headers = _role_headers(client, "admin_scope_reader", "admin")
    course = _create_course(client, teacher_headers, "Owner Course")
    classroom = _create_classroom(client, teacher_headers, "Owner Classroom")

    courses_response = client.get("/api/courses", headers=admin_headers)
    classroom_response = client.get(f"/api/classrooms/{classroom['id']}", headers=admin_headers)
    students_response = client.get(
        f"/api/classrooms/{classroom['id']}/students",
        headers=admin_headers,
    )
    course_patch_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=admin_headers,
        json={"title": "Admin Should Not Patch"},
    )
    assignment_response = client.post(
        f"/api/classrooms/{classroom['id']}/assignments",
        headers=admin_headers,
        json={"title": "Admin Should Not Publish"},
    )

    assert courses_response.status_code == 200
    course_items = courses_response.json()
    assert course_items[0]["title"] == "Owner Course"
    assert course_items[0]["owner_username"] == "teacher_scope_owner"
    assert classroom_response.status_code == 200
    assert classroom_response.json()["teacher_username"] == "teacher_scope_owner"
    assert students_response.status_code == 200
    assert course_patch_response.status_code == 403
    assert assignment_response.status_code == 403


def test_teaching_manager_can_manage_teacher_course_and_classroom(client):
    teacher_headers = _auth_headers(client, "teacher_managed_owner")
    manager_headers = _role_headers(client, "teaching_manager_scope", "teaching_manager")
    course = _create_course(client, teacher_headers, "Managed Course")
    classroom = _create_classroom(client, teacher_headers, "Managed Classroom")

    patch_response = client.patch(
        f"/api/courses/{course['id']}",
        headers=manager_headers,
        json={"title": "Manager Updated Course"},
    )
    assignment_response = client.post(
        f"/api/classrooms/{classroom['id']}/assignments",
        headers=manager_headers,
        json={"title": "Manager Published Assignment"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Manager Updated Course"
    assert assignment_response.status_code == 201
    assert assignment_response.json()["title"] == "Manager Published Assignment"
