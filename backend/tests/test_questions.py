def _auth_headers(client, username: str = "teacher_questions") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Question Teacher",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_question(client, headers: dict[str, str], **overrides):
    payload = {
        "title": "Matrix multiplication condition",
        "subject": "Math",
        "question_type": "single_choice",
        "difficulty": "basic",
        "stem": "When does matrix product AB exist?",
        "options": [
            "A. Columns of A equal rows of B",
            "B. Rows of A equal columns of B",
            "C. The two matrices must be identical",
            "D. Any matrices can be multiplied",
        ],
        "answer": "A",
        "analysis": "Matrix multiplication requires columns of the first matrix to equal rows of the second matrix.",
        "tags": ["matrix", "linear-algebra"],
    }
    payload.update(overrides)
    response = client.post("/api/questions", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def _create_course(client, headers: dict[str, str], **overrides):
    payload = {
        "title": "Math Foundation",
        "subject": "Math",
        "exam_type": "postgraduate",
        "description": "Question bank linkage course.",
        "status": "active",
    }
    payload.update(overrides)
    response = client.post("/api/courses", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_question_crud_filters_and_options(client):
    headers = _auth_headers(client)
    question = _create_question(client, headers)

    list_response = client.get(
        "/api/questions?subject=Math&difficulty=basic&status=draft",
        headers=headers,
    )
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == question["id"]
    assert items[0]["options"][0].startswith("A. Columns")
    assert items[0]["tags"] == ["matrix", "linear-algebra"]

    patch_response = client.patch(
        f"/api/questions/{question['id']}",
        headers=headers,
        json={"difficulty": "medium", "analysis": "Updated analysis"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["difficulty"] == "medium"
    assert patch_response.json()["analysis"] == "Updated analysis"


def test_question_bulk_create_saves_multiple_drafts(client):
    headers = _auth_headers(client, "teacher_question_bulk")

    response = client.post(
        "/api/questions/bulk",
        headers=headers,
        json={
            "questions": [
                {
                    "title": "Limit definition",
                    "subject": "数学",
                    "question_type": "single_choice",
                    "difficulty": "basic",
                    "stem": r"函数 \(f(x)\) 在 \(x=0\) 连续的条件是什么？",
                    "options": ["A. 左极限存在", "B. 右极限存在", "C. 函数值存在", "D. 极限存在且等于函数值"],
                    "answer": "D",
                    "analysis": "连续要求函数极限等于函数值。",
                    "tags": ["极限", "连续"],
                },
                {
                    "title": "Derivative meaning",
                    "subject": "数学",
                    "question_type": "short_answer",
                    "difficulty": "medium",
                    "stem": "说明导数的几何意义。",
                    "answer": "切线斜率",
                    "analysis": "导数表示曲线在该点切线的斜率。",
                    "tags": ["导数"],
                },
            ],
        },
    )

    assert response.status_code == 201
    items = response.json()
    assert len(items) == 2
    assert [item["status"] for item in items] == ["draft", "draft"]
    assert items[0]["options"][3].startswith("D.")
    assert items[1]["answer"] == "切线斜率"

    list_response = client.get("/api/questions?subject=数学", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2


def test_question_scope_and_delete(client):
    owner_headers = _auth_headers(client, "teacher_question_owner")
    other_headers = _auth_headers(client, "teacher_question_other")
    question = _create_question(client, owner_headers)

    other_detail = client.get(
        f"/api/questions/{question['id']}",
        headers=other_headers,
    )
    assert other_detail.status_code == 404

    delete_response = client.delete(
        f"/api/questions/{question['id']}",
        headers=owner_headers,
    )
    assert delete_response.status_code == 204

    missing_response = client.get(
        f"/api/questions/{question['id']}",
        headers=owner_headers,
    )
    assert missing_response.status_code == 404


def test_question_patch_rejects_null_non_nullable_fields(client):
    headers = _auth_headers(client, "teacher_question_patch_nulls")
    question = _create_question(client, headers)

    null_title_response = client.patch(
        f"/api/questions/{question['id']}",
        headers=headers,
        json={"title": None},
    )
    null_difficulty_response = client.patch(
        f"/api/questions/{question['id']}",
        headers=headers,
        json={"difficulty": None},
    )
    detail_response = client.get(f"/api/questions/{question['id']}", headers=headers)

    assert null_title_response.status_code == 422
    assert null_difficulty_response.status_code == 422
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Matrix multiplication condition"
    assert detail_response.json()["difficulty"] == "basic"


def test_question_course_link_ownership_scope(client):
    owner_headers = _auth_headers(client, "teacher_question_course_owner")
    other_headers = _auth_headers(client, "teacher_question_course_other")
    owner_course = _create_course(client, owner_headers)

    forbidden_response = client.post(
        "/api/questions",
        headers=other_headers,
        json={
            "title": "Forbidden course link",
            "subject": "Math",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "This should not link to another user's course.",
            "course_id": owner_course["id"],
        },
    )
    assert forbidden_response.status_code == 404

    linked_question = _create_question(
        client,
        owner_headers,
        course_id=owner_course["id"],
    )
    assert linked_question["course_id"] == owner_course["id"]


def test_question_validates_supported_type_and_difficulty(client):
    headers = _auth_headers(client, "teacher_question_validation")

    invalid_type_response = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "Invalid type",
            "subject": "Math",
            "question_type": "essay",
            "difficulty": "basic",
            "stem": "Unsupported question type.",
        },
    )
    invalid_difficulty_response = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "Invalid difficulty",
            "subject": "Math",
            "question_type": "short_answer",
            "difficulty": "expert",
            "stem": "Unsupported difficulty.",
        },
    )

    assert invalid_type_response.status_code == 422
    assert invalid_difficulty_response.status_code == 422


def test_save_exercise_content_to_question_bank_drafts(client):
    headers = _auth_headers(client, "teacher_question_from_exercise")
    exercise_response = client.post(
        "/api/exercises",
        headers=headers,
        json={
            "title": "矩阵乘法课堂练习",
            "subject": "数学",
            "knowledge_point": "矩阵乘法",
            "question_type": "选择题",
            "difficulty": "基础",
            "content": (
                "题目 1\n"
                "矩阵 A 为 2×3，矩阵 B 为 3×2，AB 的结果阶数是？\n"
                "A. 2×2\n"
                "B. 3×3\n"
                "C. 2×3\n"
                "D. 不存在\n"
                "答案：A\n"
                "解析：A 的列数等于 B 的行数，结果为 2×2。\n\n"
                "题目 2\n"
                "矩阵乘法 AB 存在的条件是什么？\n"
                "A. A 的行数等于 B 的列数\n"
                "B. A 的列数等于 B 的行数\n"
                "C. 两个矩阵必须相同\n"
                "D. 任意矩阵都可以相乘\n"
                "答案：B\n"
                "解析：矩阵乘法要求前一个矩阵的列数等于后一个矩阵的行数。"
            ),
        },
    )
    assert exercise_response.status_code == 201
    exercise = exercise_response.json()

    response = client.post(
        f"/api/exercises/{exercise['id']}/save-to-question-bank",
        headers=headers,
    )

    assert response.status_code == 201
    items = response.json()
    assert len(items) == 2
    assert all(item["source_exercise_id"] == exercise["id"] for item in items)
    assert all(item["subject"] == "数学" for item in items)
    assert all(item["question_type"] == "single_choice" for item in items)
    assert all(item["difficulty"] == "basic" for item in items)
    assert items[0]["title"] == "矩阵乘法课堂练习 - 题目 1"
    assert items[0]["options"] == ["A. 2×2", "B. 3×3", "C. 2×3", "D. 不存在"]
    assert items[0]["answer"] == "A"
    assert "结果为 2×2" in items[0]["analysis"]

    list_response = client.get("/api/questions?subject=数学&status=draft", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
