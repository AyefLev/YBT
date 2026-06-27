def _auth_headers(client, username: str = "compliance_teacher") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": username.title(),
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def test_compliance_check_requires_authentication(client):
    response = client.post(
        "/api/compliance/check",
        json={"content_type": "lesson", "content": "safe content"},
    )

    assert response.status_code == 401


def test_compliance_check_flags_high_risk_promise_terms(client):
    response = client.post(
        "/api/compliance/check",
        headers=_auth_headers(client, "compliance_high_risk"),
        json={"content_type": "lesson", "content": "本课程保证上岸，100%通过。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "high"
    assert "保证上岸" in payload["matched_terms"]
    assert "100%通过" in payload["matched_terms"]
    assert payload["suggestions"]


def test_compliance_check_privacy_only_is_medium_risk(client):
    response = client.post(
        "/api/compliance/check",
        headers=_auth_headers(client, "compliance_privacy"),
        json={
            "content_type": "material",
            "content": "请联系 13800138000 或 teacher@example.com。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "medium"
    assert "手机号" in payload["matched_terms"]
    assert "邮箱" in payload["matched_terms"]


def test_compliance_check_safe_content_is_low_risk(client):
    response = client.post(
        "/api/compliance/check",
        headers=_auth_headers(client, "compliance_safe"),
        json={"content_type": "lesson", "content": "本节课讲解阅读理解方法。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "low"
    assert payload["matched_terms"] == []


def test_check_content_does_not_commit_pending_caller_changes(client):
    from app.compliance.service import check_content
    from app.core.database import get_session_local
    from app.logs.models import OperationLog

    session_local = get_session_local()
    with session_local() as db:
        db.add(OperationLog(action="pending-compliance-transaction-boundary"))
        check_content(db, "lesson", "本节课讲解阅读理解方法。")
        db.rollback()

    with session_local() as db:
        persisted = (
            db.query(OperationLog)
            .filter(OperationLog.action == "pending-compliance-transaction-boundary")
            .first()
        )

    assert persisted is None
