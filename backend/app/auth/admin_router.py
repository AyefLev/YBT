from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Permission, Role, User
from app.auth.schemas import TeacherReviewRequest, UserCreate, UserUpdate
from app.auth.service import (
    approve_teacher_application,
    create_user_by_admin,
    reject_teacher_application,
    update_user_by_admin,
)
from app.core.database import get_db
from app.core.deps import require_permission

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RoleRead(BaseModel):
    id: int
    name: str
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    permissions: list[str] = Field(default_factory=list)


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list)


class AdminUserRead(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    is_active: bool
    requested_role: str
    account_status: str
    review_note: str
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    roles: list[str]
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list)


def _role_to_read(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        permissions=sorted(permission.code for permission in role.permissions),
    )


def _user_to_read(user: User) -> AdminUserRead:
    return AdminUserRead(
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


def _load_permissions(db: Session, codes: list[str]) -> list[Permission]:
    unique_codes = sorted(set(codes))
    if not unique_codes:
        return []

    permissions = list(
        db.scalars(select(Permission).where(Permission.code.in_(unique_codes))).all()
    )
    found_codes = {permission.code for permission in permissions}
    missing_codes = sorted(set(unique_codes) - found_codes)
    if missing_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission codes: {', '.join(missing_codes)}",
        )
    return sorted(permissions, key=lambda permission: permission.code)


def _load_roles(db: Session, names: list[str]) -> list[Role]:
    unique_names = sorted(set(names))
    if not unique_names:
        return []

    roles = list(db.scalars(select(Role).where(Role.name.in_(unique_names))).all())
    found_names = {role.name for role in roles}
    missing_names = sorted(set(unique_names) - found_names)
    if missing_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role names: {', '.join(missing_names)}",
        )
    return sorted(roles, key=lambda role: role.name)


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    current_user: User = Depends(require_permission("admin:role_manage")),
    db: Session = Depends(get_db),
) -> list[RoleRead]:
    _ = current_user
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [_role_to_read(role) for role in roles]


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_permission("admin:role_manage")),
    db: Session = Depends(get_db),
) -> RoleRead:
    _ = current_user
    existing_role = db.scalar(select(Role).where(Role.name == payload.name))
    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists",
        )

    role = Role(name=payload.name, permissions=_load_permissions(db, payload.permissions))
    db.add(role)
    db.commit()
    db.refresh(role)
    return _role_to_read(role)


@router.post("/roles/{role_id}/permissions", response_model=RoleRead)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    current_user: User = Depends(require_permission("admin:role_manage")),
    db: Session = Depends(get_db),
) -> RoleRead:
    _ = current_user
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    role.permissions = _load_permissions(db, payload.permissions)
    db.commit()
    db.refresh(role)
    return _role_to_read(role)


@router.get("/users", response_model=list[AdminUserRead])
def list_users(
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> list[AdminUserRead]:
    _ = current_user
    users = db.scalars(select(User).order_by(User.id)).all()
    return [_user_to_read(user) for user in users]


@router.post("/users", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    _ = current_user
    user = create_user_by_admin(db, payload)
    return _user_to_read(user)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    _ = current_user
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_read(update_user_by_admin(db, user=user, payload=payload))


@router.post("/users/{user_id}/roles", response_model=AdminUserRead)
def update_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    _ = current_user
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.roles = _load_roles(db, payload.roles)
    db.commit()
    db.refresh(user)
    return _user_to_read(user)


@router.delete("/users/{user_id}", response_model=AdminUserRead)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current admin account cannot deactivate itself",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return _user_to_read(user)


@router.get("/teacher-applications", response_model=list[AdminUserRead])
def list_teacher_applications(
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> list[AdminUserRead]:
    _ = current_user
    users = db.scalars(
        select(User)
        .where(User.requested_role == "teacher", User.account_status == "pending")
        .order_by(User.id)
    ).all()
    return [_user_to_read(user) for user in users]


@router.post("/teacher-applications/{user_id}/approve", response_model=AdminUserRead)
def approve_teacher(
    user_id: int,
    payload: TeacherReviewRequest,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_read(
        approve_teacher_application(db, user=user, reviewer=current_user, note=payload.note)
    )


@router.post("/teacher-applications/{user_id}/reject", response_model=AdminUserRead)
def reject_teacher(
    user_id: int,
    payload: TeacherReviewRequest,
    current_user: User = Depends(require_permission("admin:user_manage")),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_read(
        reject_teacher_application(db, user=user, reviewer=current_user, note=payload.note)
    )
