from io import BytesIO

from docx import Document


def _auth_headers(client, username: str = "teacher_phase3_exports") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Export Teacher",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _docx_text(response) -> str:
    document = Document(BytesIO(response.content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def test_export_course_outline_docx(client):
    headers = _auth_headers(client)
    course = client.post(
        "/api/courses",
        headers=headers,
        json={
            "title": "Postgraduate English Foundation",
            "subject": "English",
            "exam_type": "postgraduate",
            "description": "Foundation course for writing.",
            "status": "active",
        },
    ).json()
    chapter = client.post(
        f"/api/courses/{course['id']}/chapters",
        headers=headers,
        json={
            "title": "Letter Writing",
            "summary": "Small composition formats.",
            "order_index": 1,
        },
    ).json()
    session = client.post(
        f"/api/chapters/{chapter['id']}/sessions",
        headers=headers,
        json={
            "title": "Advice Letter Practice",
            "duration_minutes": 90,
            "teaching_goal": "Master structure and tone.",
            "order_index": 1,
        },
    ).json()
    client.post(
        f"/api/courses/{course['id']}/knowledge-points",
        headers=headers,
        json={
            "chapter_id": chapter["id"],
            "session_id": session["id"],
            "name": "Advice letter structure",
            "description": "Purpose, suggestions, closing.",
            "difficulty": "basic",
        },
    )

    response = client.post(
        f"/api/exports/course/{course['id']}/outline-docx",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.content.startswith(b"PK")
    text = _docx_text(response)
    assert "Postgraduate English Foundation" in text
    assert "Letter Writing" in text
    assert "Advice Letter Practice" in text
    assert "Advice letter structure" in text


def test_export_question_package_docx(client):
    headers = _auth_headers(client, "teacher_question_export")
    question = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "Letter format",
            "subject": "English",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "What parts does an advice letter usually include?",
            "options": [],
            "answer": "Purpose, specific suggestions, and closing.",
            "analysis": "An advice letter should state the purpose and then provide concrete suggestions.",
            "tags": ["writing"],
        },
    ).json()

    response = client.post(
        "/api/exports/questions/docx",
        headers=headers,
        json={"question_ids": [question["id"]]},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"PK")
    text = _docx_text(response)
    assert "Letter format" in text
    assert "What parts does an advice letter usually include?" in text
    assert "Purpose, specific suggestions, and closing." in text
    assert "An advice letter should state the purpose" in text


def test_cross_user_cannot_export_question_package(client):
    owner_headers = _auth_headers(client, "teacher_question_export_owner")
    other_headers = _auth_headers(client, "teacher_question_export_other")
    question = client.post(
        "/api/questions",
        headers=owner_headers,
        json={
            "title": "Private question",
            "subject": "Math",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "Private stem",
            "answer": "Private answer",
        },
    ).json()

    owner_response = client.post(
        "/api/exports/questions/docx",
        headers=owner_headers,
        json={"question_ids": [question["id"]]},
    )
    response = client.post(
        "/api/exports/questions/docx",
        headers=other_headers,
        json={"question_ids": [question["id"]]},
    )

    assert owner_response.status_code == 200
    assert response.status_code == 404
