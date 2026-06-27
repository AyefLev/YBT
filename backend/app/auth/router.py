from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.schemas import Token, UserLogin, UserRead, UserRegister
from app.auth.service import authenticate_user, create_user_access_token, register_user
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        requested_role=user.requested_role,
        account_status=user.account_status,
        review_note=user.review_note,
        reviewed_by_id=user.reviewed_by_id,
        reviewed_at=user.reviewed_at,
        roles=user.role_names,
        permissions=user.permission_codes,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> UserRead:
    return user_to_read(register_user(db, payload))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_user_access_token(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return user_to_read(current_user)
