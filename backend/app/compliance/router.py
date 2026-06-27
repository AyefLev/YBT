from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.compliance.schemas import ComplianceCheckRequest, ComplianceCheckResponse
from app.compliance.service import check_content
from app.auth.models import User
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.post("/check", response_model=ComplianceCheckResponse)
def check_compliance(
    payload: ComplianceCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComplianceCheckResponse:
    _ = current_user
    response = check_content(
        db=db,
        content_type=payload.content_type,
        content=payload.content,
        content_id=payload.content_id,
    )
    db.commit()
    return response
