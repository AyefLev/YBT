def _auth_headers(client, username: str = "teacher_materials") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Materials Teacher",
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


def _upload_txt(client, headers: dict[str, str], title: str, content: str):
    return client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": title},
        files={"file": ("writing.txt", content.encode("utf-8"), "text/plain")},
    )


def _upload_txt_with_scope(
    client,
    headers: dict[str, str],
    title: str,
    content: str,
    resource_scope: str,
):
    return client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": title, "resource_scope": resource_scope},
        files={"file": ("scoped.txt", content.encode("utf-8"), "text/plain")},
    )


def _blank_pdf_bytes() -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(output)
    return output.getvalue()


def test_upload_txt_material_and_retrieve_chinese_query(client):
    headers = _auth_headers(client)

    upload_response = _upload_txt(client, headers, "小作文资料", "小作文 格式 称呼 正文 结尾")

    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["title"] == "小作文资料"
    assert uploaded["file_name"] == "writing.txt"
    assert uploaded["file_type"] == ".txt"
    assert uploaded["parse_status"] == "parsed"
    assert uploaded["chunk_count"] > 0

    search_response = client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "小作文格式", "top_k": 5, "material_ids": [uploaded["id"]]},
    )

    assert search_response.status_code == 200
    assert search_response.json()["retrieval_mode"] == "lexical"
    results = search_response.json()["chunks"]
    assert results
    assert results[0]["material_id"] == uploaded["id"]
    assert "小作文" in results[0]["content"]


def test_material_chunks_strip_nul_characters_before_storage(client):
    headers = _auth_headers(client, username="teacher_nul_material")

    upload_response = _upload_txt(
        client,
        headers,
        "NUL Character Material",
        "matrix\x00 multiplication",
    )

    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["parse_status"] == "parsed"

    chunks_response = client.get(
        f"/api/materials/{uploaded['id']}/chunks",
        headers=headers,
    )

    assert chunks_response.status_code == 200
    chunks = chunks_response.json()
    assert chunks
    assert "\x00" not in chunks[0]["content"]
    assert "matrix multiplication" in chunks[0]["content"]


def test_reparse_clears_stale_chunks_before_next_parse_finishes(client):
    from app.core.database import get_session_local
    from app.materials.models import Material
    from app.materials.service import mark_material_for_reparse

    headers = _auth_headers(client, username="teacher_reparse_clears_stale_chunks")
    upload_response = _upload_txt(
        client,
        headers,
        "Stale Chunk Material",
        "old extracted content should not remain during reparse",
    )

    assert upload_response.status_code == 201
    material_id = upload_response.json()["id"]
    before_response = client.get(f"/api/materials/{material_id}/chunks", headers=headers)
    assert before_response.status_code == 200
    assert before_response.json()

    session_local = get_session_local()
    with session_local() as db:
        material = db.get(Material, material_id)
        mark_material_for_reparse(db, material=material)
        db.commit()

    after_response = client.get(f"/api/materials/{material_id}/chunks", headers=headers)
    assert after_response.status_code == 200
    assert after_response.json() == []


def test_owner_can_retrieve_without_material_ids(client):
    headers = _auth_headers(client, username="teacher_owner")
    upload_response = _upload_txt(client, headers, "Owner Material", "小作文 格式 称呼 正文 结尾")
    material_id = upload_response.json()["id"]

    search_response = client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "小作文格式", "top_k": 5, "material_ids": []},
    )

    assert search_response.status_code == 200
    results = search_response.json()["chunks"]
    assert results
    assert results[0]["material_id"] == material_id


def test_retrieval_is_scoped_to_current_user_materials(client):
    owner_headers = _auth_headers(client, username="teacher_owner_a")
    other_headers = _auth_headers(client, username="teacher_owner_b")
    upload_response = _upload_txt(client, owner_headers, "Private Material", "小作文 格式 称呼 正文 结尾")
    owner_material_id = upload_response.json()["id"]

    unrestricted_response = client.post(
        "/api/retrieval/search",
        headers=other_headers,
        json={"query": "小作文格式", "top_k": 5, "material_ids": []},
    )
    guessed_id_response = client.post(
        "/api/retrieval/search",
        headers=other_headers,
        json={"query": "小作文格式", "top_k": 5, "material_ids": [owner_material_id]},
    )

    assert unrestricted_response.status_code == 200
    assert guessed_id_response.status_code == 200
    assert unrestricted_response.json()["chunks"] == []
    assert guessed_id_response.json()["chunks"] == []


def test_public_and_personal_material_domains_are_enforced(client):
    owner_headers = _auth_headers(client, username="teacher_material_domain_owner")
    other_headers = _auth_headers(client, username="teacher_material_domain_other")
    manager_headers = _role_headers(client, "manager_material_domain", "teaching_manager")
    admin_headers = _role_headers(client, "admin_material_domain", "admin")

    private_material = _upload_txt_with_scope(
        client,
        owner_headers,
        "Private Domain Material",
        "private-only calculus material",
        "personal",
    ).json()
    forbidden_public = _upload_txt_with_scope(
        client,
        owner_headers,
        "Teacher Public Attempt",
        "teacher should not publish public material",
        "public",
    )
    public_material = _upload_txt_with_scope(
        client,
        manager_headers,
        "Public Domain Material",
        "shared-public calculus material",
        "public",
    ).json()

    other_list_response = client.get("/api/materials", headers=other_headers)
    other_search_response = client.post(
        "/api/retrieval/search",
        headers=other_headers,
        json={"query": "calculus", "top_k": 5, "material_ids": []},
    )
    manager_delete_private_response = client.delete(
        f"/api/materials/{private_material['id']}",
        headers=manager_headers,
    )
    admin_delete_private_response = client.delete(
        f"/api/materials/{private_material['id']}",
        headers=admin_headers,
    )

    assert forbidden_public.status_code == 403
    assert public_material["resource_scope"] == "public"
    assert public_material["uploader_username"] == "manager_material_domain"

    assert other_list_response.status_code == 200
    visible_titles = {material["title"] for material in other_list_response.json()}
    assert "Public Domain Material" in visible_titles
    assert "Private Domain Material" not in visible_titles

    assert other_search_response.status_code == 200
    result_ids = {chunk["material_id"] for chunk in other_search_response.json()["chunks"]}
    assert public_material["id"] in result_ids
    assert private_material["id"] not in result_ids

    assert manager_delete_private_response.status_code == 403
    assert admin_delete_private_response.status_code == 403


def test_retrieval_search_uses_user_scoped_cache(client):
    headers = _auth_headers(client, username="teacher_retrieval_cache")
    upload_response = _upload_txt(client, headers, "Cached Retrieval", "小作文 格式 称呼 正文 结尾")
    material_id = upload_response.json()["id"]
    payload = {"query": "小作文格式", "top_k": 5, "material_ids": [material_id]}

    first_response = client.post("/api/retrieval/search", headers=headers, json=payload)
    second_response = client.post("/api/retrieval/search", headers=headers, json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["cache_hit"] is False
    assert second_response.json()["cache_hit"] is True
    assert first_response.json()["retrieval_mode"] == "lexical"
    assert second_response.json()["retrieval_mode"] == "lexical"
    assert second_response.json()["chunks"] == first_response.json()["chunks"]


def test_retrieval_cache_does_not_cross_users(client):
    owner_headers = _auth_headers(client, username="teacher_retrieval_cache_owner")
    other_headers = _auth_headers(client, username="teacher_retrieval_cache_other")
    upload_response = _upload_txt(client, owner_headers, "Owner Cached Retrieval", "小作文 格式 称呼 正文 结尾")
    material_id = upload_response.json()["id"]
    payload = {"query": "小作文格式", "top_k": 5, "material_ids": [material_id]}

    owner_response = client.post("/api/retrieval/search", headers=owner_headers, json=payload)
    other_response = client.post("/api/retrieval/search", headers=other_headers, json=payload)

    assert owner_response.status_code == 200
    assert other_response.status_code == 200
    assert owner_response.json()["chunks"]
    assert other_response.json()["chunks"] == []
    assert other_response.json()["cache_hit"] is False


def test_malformed_docx_upload_records_failed_parse_status(client):
    from app.core.config import get_settings

    headers = _auth_headers(client, username="teacher_bad_docx")
    upload_dir = get_settings().upload_dir
    before_files = set(upload_dir.iterdir())

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Bad Docx"},
        files={
            "file": (
                "broken.docx",
                b"this is not a valid docx archive",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "failed"
    assert body["parse_error"]
    assert len(set(upload_dir.iterdir()) - before_files) == 1


def test_scanned_pdf_without_vision_is_marked_as_needing_vision(client):
    headers = _auth_headers(client, username="teacher_scanned_pdf_needs_vision")

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Scanned Math PDF"},
        files={"file": ("scanned.pdf", _blank_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "needs_vision"
    assert "视觉模型" in body["parse_error"]
    assert body["chunk_count"] == 0


def test_pdf_garbled_control_characters_are_low_quality_text():
    from app.materials.parsers import _is_low_quality_extracted_text

    garbled = "".join(
        [
            "\x03\x05\n\x06\n\x02\x07\x0e\x01\x0f\x10\t\x08\x10\x04 ",
            "\x8f\x98",
            chr(0x01A3),
            "\n\x05\t\x11\n\x10\x12\x0f\x04\n",
            chr(0x019D),
            chr(0x0191),
            "MG",
            chr(0x0113),
            chr(0x0192),
            chr(0x0110),
        ]
    )
    readable = "2025版强化36讲勘误汇总\n高数第18讲 数列极限三向解题法 P68"

    assert _is_low_quality_extracted_text(garbled) is True
    assert _is_low_quality_extracted_text(readable) is False


def test_scanned_pdf_uses_vision_fallback_when_available(client, monkeypatch):
    from app.ai.schemas import AIResult
    from app.materials.vision import RenderedPage
    import app.materials.service as material_service

    headers = _auth_headers(client, username="teacher_scanned_pdf_vision")

    monkeypatch.setattr(
        material_service,
        "render_pdf_pages_for_vision",
        lambda _path: [
            RenderedPage(
                page_no=1,
                image_bytes=b"\x89PNG\r\n\x1a\nrendered-page",
                mime_type="image/png",
            )
        ],
    )

    def fake_analyze_image(db, *, image_bytes, mime_type, prompt, user_id=None):
        assert image_bytes.startswith(b"\x89PNG")
        assert mime_type == "image/png"
        assert "考研" in prompt
        assert user_id is not None
        return AIResult(
            content="导数定义：设函数 y=f(x)，导数刻画自变量微小变化下函数值的变化率。",
            provider="real",
            model="vision-model",
            fallback_used=False,
        )

    monkeypatch.setattr(material_service, "analyze_image", fake_analyze_image)

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Vision Parsed PDF"},
        files={"file": ("scanned.pdf", _blank_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "parsed"
    assert body["parse_error"] in (None, "")
    assert body["chunk_count"] == 1

    chunks_response = client.get(f"/api/materials/{body['id']}/chunks", headers=headers)

    assert chunks_response.status_code == 200
    chunks = chunks_response.json()
    assert chunks[0]["page_no"] == 1
    assert "导数定义" in chunks[0]["content"]


def test_retrieval_ignores_single_shared_chinese_character(client):
    headers = _auth_headers(client, username="teacher_single_hit")
    _upload_txt(client, headers, "Weak Match", "格")

    response = client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "小作文格式", "top_k": 5, "material_ids": []},
    )

    assert response.status_code == 200
    assert response.json()["chunks"] == []


def test_upload_rejects_unsupported_suffix(client):
    headers = _auth_headers(client, username="teacher_unsupported")

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Unsupported"},
        files={"file": ("notes.exe", b"not a material", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_retrieval_requires_authorization(client):
    response = client.post(
        "/api/retrieval/search",
        json={"query": "小作文格式", "top_k": 5, "material_ids": []},
    )

    assert response.status_code in {401, 403}


def test_phase2_material_upload_accepts_metadata_and_exposes_management_apis(client):
    headers = _auth_headers(client, username="teacher_phase2_material")

    upload_response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={
            "title": "Matrix Notes",
            "subject": "Math",
            "purpose": "lesson",
            "tags": "linear algebra,exam",
        },
        files={
            "file": (
                "matrix.txt",
                b"matrix multiplication requires matching inner dimensions",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["subject"] == "Math"
    assert uploaded["purpose"] == "lesson"
    assert uploaded["tags"] == ["linear algebra", "exam"]
    assert uploaded["parse_error"] in (None, "")
    assert uploaded["parse_status"] in {"pending", "parsing", "parsed"}

    detail_response = client.get(f"/api/materials/{uploaded['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == uploaded["id"]
    assert detail["title"] == "Matrix Notes"
    assert detail["chunk_count"] > 0

    list_response = client.get("/api/materials", headers=headers)
    assert list_response.status_code == 200
    materials = list_response.json()
    assert [material["title"] for material in materials] == ["Matrix Notes"]

    chunks_response = client.get(f"/api/materials/{uploaded['id']}/chunks", headers=headers)
    assert chunks_response.status_code == 200
    chunks = chunks_response.json()
    assert chunks
    assert chunks[0]["material_id"] == uploaded["id"]
    assert "matching inner dimensions" in chunks[0]["content"]


def test_phase2_reparse_delete_and_search_provenance(client):
    headers = _auth_headers(client, username="teacher_phase2_reparse")
    upload_response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Letter Writing", "subject": "English"},
        files={
            "file": (
                "letter.txt",
                b"business letter format greeting body closing signature",
                "text/plain",
            )
        },
    )
    material_id = upload_response.json()["id"]

    reparse_response = client.post(f"/api/materials/{material_id}/reparse", headers=headers)
    assert reparse_response.status_code == 202
    assert reparse_response.json()["parse_status"] in {"pending", "parsing", "parsed"}

    search_response = client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "letter format", "top_k": 5, "material_ids": [material_id]},
    )
    assert search_response.status_code == 200
    result = search_response.json()["chunks"][0]
    assert result["material_id"] == material_id
    assert result["material_title"] == "Letter Writing"
    assert result["source"] == "Letter Writing"

    delete_response = client.delete(f"/api/materials/{material_id}", headers=headers)
    assert delete_response.status_code == 204
    missing_response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert missing_response.status_code == 404


def test_phase2_parse_failure_is_recorded_on_material_and_job_log(client):
    from app.core.database import get_session_local
    from app.logs.models import JobLog

    headers = _auth_headers(client, username="teacher_phase2_parse_failure")

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        data={"title": "Broken Docx", "subject": "English"},
        files={
            "file": (
                "broken.docx",
                b"this is not a valid docx archive",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "failed"
    assert body["parse_error"]

    session_local = get_session_local()
    with session_local() as db:
        logs = db.query(JobLog).filter(JobLog.resource_id == body["id"]).all()
        assert logs
        assert logs[-1].status == "failed"
        assert logs[-1].error_message


def test_material_parse_status_endpoint_reads_cached_job_state(client):
    import json

    from app.cache.service import get_cache

    headers = _auth_headers(client, username="teacher_material_status_cache")
    upload_response = _upload_txt(client, headers, "Cached Status", "matrix multiplication")
    material_id = upload_response.json()["id"]
    get_cache().set(
        f"material:{material_id}:parse_status",
        json.dumps(
            {
                "material_id": material_id,
                "status": "parsing",
                "detail": "Parsing cached status",
                "error_message": "",
            }
        ),
        ttl_seconds=30,
    )

    response = client.get(f"/api/materials/{material_id}/parse-status", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == material_id
    assert body["status"] == "parsing"
    assert body["detail"] == "Parsing cached status"
    assert body["cache_hit"] is True


def test_material_parse_status_endpoint_falls_back_to_database(client):
    from app.cache.service import get_cache

    headers = _auth_headers(client, username="teacher_material_status_db")
    upload_response = _upload_txt(client, headers, "Database Status", "matrix multiplication")
    material_id = upload_response.json()["id"]
    get_cache().delete(f"material:{material_id}:parse_status")

    response = client.get(f"/api/materials/{material_id}/parse-status", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == material_id
    assert body["status"] == upload_response.json()["parse_status"]
    assert body["cache_hit"] is False
