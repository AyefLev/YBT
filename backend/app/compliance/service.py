import json
import re

from sqlalchemy.orm import Session

from app.compliance.models import ComplianceLog
from app.compliance.schemas import ComplianceCheckResponse

HIGH_RISK_TERMS = (
    "保证上岸",
    "100%通过",
    "必过",
    "保分",
    "内部押题",
    "命题人参与",
)

PRIVACY_PATTERNS = (
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("邮箱", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    (
        "身份证号",
        re.compile(r"(?<![0-9Xx])\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?![0-9Xx])"),
    ),
)


def check_content(
    db: Session,
    content_type: str,
    content: str,
    content_id: str | None = None,
) -> ComplianceCheckResponse:
    matched_terms = _find_matches(content)
    risk_level = _risk_level(matched_terms)
    suggestions = _suggestions(risk_level)
    response = ComplianceCheckResponse(
        risk_level=risk_level,
        matched_terms=matched_terms,
        suggestions=suggestions,
    )

    db.add(
        ComplianceLog(
            content_type=content_type,
            content_id=content_id,
            risk_level=risk_level,
            matched_terms=json.dumps(matched_terms, ensure_ascii=False),
            suggestions=json.dumps(suggestions, ensure_ascii=False),
        )
    )
    db.flush()

    return response


def _find_matches(content: str) -> list[str]:
    matches: list[str] = []
    for term in HIGH_RISK_TERMS:
        if term in content:
            matches.append(term)

    for label, pattern in PRIVACY_PATTERNS:
        if pattern.search(content) and label not in matches:
            matches.append(label)

    return matches


def _risk_level(matched_terms: list[str]) -> str:
    if any(term in HIGH_RISK_TERMS for term in matched_terms):
        return "high"
    if matched_terms:
        return "medium"
    return "low"


def _suggestions(risk_level: str) -> list[str]:
    if risk_level == "high":
        return ["删除或改写升学结果承诺、押题等高风险表述。"]
    if risk_level == "medium":
        return ["移除或脱敏个人手机号、邮箱、身份证号等隐私信息。"]
    return []
