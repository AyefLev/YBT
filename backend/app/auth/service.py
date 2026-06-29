from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Permission, Role, User
from app.auth.permissions import PERMISSION_CODES, ROLE_PERMISSIONS
from app.auth.schemas import UserCreate, UserRegister, UserUpdate
from app.core.config import Settings
from app.core.security import create_access_token, get_password_hash, verify_password

AUTO_ADD_PERMISSION_CODES = {
    "review:manage",
    "material:view_public",
    "material:publish_public",
    "material:manage_all",
    "course:create",
    "course:manage_all",
    "class:manage",
    "class:manage_all",
    "class:join",
    "assignment:manage",
    "assignment:submit",
    "assignment:grade",
    "admin:content_manage",
    "lesson:view_all",
    "exercise:view_all",
    "material:view_all",
    "course:view_all",
    "class:view_all",
    "assignment:view_all",
    "question:view_all",
}
SYNC_ROLE_PERMISSION_NAMES = {"admin"}
REMOVE_ROLE_PERMISSION_CODES = {
    "teaching_manager": {"lesson:create", "exercise:create"},
}


def seed_default_auth_data(db: Session) -> None:
    permissions_by_code = {
        permission.code: permission
        for permission in db.scalars(select(Permission)).all()
    }
    for code in PERMISSION_CODES:
        if code not in permissions_by_code:
            permission = Permission(code=code)
            permissions_by_code[code] = permission
            db.add(permission)
    db.flush()

    roles_by_name = {role.name: role for role in db.scalars(select(Role)).all()}
    for name, permission_codes in ROLE_PERMISSIONS.items():
        permissions = [permissions_by_code[code] for code in permission_codes]
        if name in roles_by_name:
            role = roles_by_name[name]
            if name in SYNC_ROLE_PERMISSION_NAMES:
                role.permissions = permissions
                continue
            removed_codes = REMOVE_ROLE_PERMISSION_CODES.get(name, set())
            if removed_codes:
                role.permissions = [
                    permission
                    for permission in role.permissions
                    if permission.code not in removed_codes
                ]
            current_codes = {permission.code for permission in role.permissions}
            missing_managed_codes = (
                set(permission_codes) & AUTO_ADD_PERMISSION_CODES
            ) - current_codes
            if missing_managed_codes:
                role.permissions = [
                    *role.permissions,
                    *[
                        permissions_by_code[code]
                        for code in sorted(missing_managed_codes)
                    ],
                ]
            continue

        role = Role(
            name=name,
            permissions=permissions,
        )
        db.add(role)

    db.commit()


def seed_bootstrap_admin(db: Session, settings: Settings) -> None:
    configured_values = [
        settings.admin_bootstrap_username,
        settings.admin_bootstrap_email,
        settings.admin_bootstrap_password,
    ]
    if not any(configured_values):
        return
    if not all(configured_values):
        raise RuntimeError(
            "ADMIN_BOOTSTRAP_USERNAME, ADMIN_BOOTSTRAP_EMAIL, and "
            "ADMIN_BOOTSTRAP_PASSWORD must be configured together."
        )
    if len(settings.admin_bootstrap_password) < 8:
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD must be at least 8 characters long.")

    admin_role = db.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        seed_default_auth_data(db)
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))

    user = db.scalar(select(User).where(User.username == settings.admin_bootstrap_username))
    existing_email = db.scalar(select(User).where(User.email == settings.admin_bootstrap_email))
    if user is None:
        if existing_email is not None:
            raise RuntimeError("ADMIN_BOOTSTRAP_EMAIL is already used by another user.")
        user = User(
            username=settings.admin_bootstrap_username,
            email=settings.admin_bootstrap_email,
            hashed_password=get_password_hash(settings.admin_bootstrap_password),
            display_name=settings.admin_bootstrap_display_name,
            roles=[admin_role],
        )
        db.add(user)
    else:
        if existing_email is not None and existing_email.id != user.id:
            raise RuntimeError("ADMIN_BOOTSTRAP_EMAIL is already used by another user.")
        user.email = settings.admin_bootstrap_email
        user.display_name = settings.admin_bootstrap_display_name
        user.hashed_password = get_password_hash(settings.admin_bootstrap_password)
        if admin_role not in user.roles:
            user.roles = [*user.roles, admin_role]

    db.commit()


def register_user(db: Session, user_in: UserRegister) -> User:
    existing_user = db.scalar(
        select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    role_name = _registration_role_name(user_in)
    role = _get_role(db, role_name)
    account_status = "pending" if role_name == "pending_teacher" else "approved"
    review_note = user_in.application_note if account_status == "pending" else ""

    user = User(
        username=user_in.username,
        email=str(user_in.email),
        hashed_password=get_password_hash(user_in.password),
        display_name=user_in.display_name,
        requested_role=user_in.role,
        account_status=account_status,
        review_note=review_note,
        roles=[role],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_by_admin(db: Session, payload: UserCreate) -> User:
    existing_user = db.scalar(
        select(User).where((User.username == payload.username) | (User.email == payload.email))
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    roles = _load_roles(db, payload.roles)
    user = User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=get_password_hash(payload.password),
        display_name=payload.display_name,
        is_active=payload.is_active,
        requested_role=payload.requested_role,
        account_status=payload.account_status,
        roles=roles,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_by_admin(db: Session, *, user: User, payload: UserUpdate) -> User:
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if value is not None:
            setattr(user, field_name, value)
    db.commit()
    db.refresh(user)
    return user


def approve_teacher_application(
    db: Session,
    *,
    user: User,
    reviewer: User,
    note: str = "",
) -> User:
    teacher_role = _get_role(db, "teacher")
    user.requested_role = "teacher"
    user.is_active = True
    user.roles = [teacher_role]
    user.mark_reviewed(reviewer_id=reviewer.id, status="approved", note=note)
    db.commit()
    db.refresh(user)
    return user


def reject_teacher_application(
    db: Session,
    *,
    user: User,
    reviewer: User,
    note: str = "",
) -> User:
    pending_role = _get_role(db, "pending_teacher")
    user.requested_role = "teacher"
    user.roles = [pending_role]
    user.mark_reviewed(reviewer_id=reviewer.id, status="rejected", note=note)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user


def create_user_access_token(user: User) -> str:
    return create_access_token(str(user.id))


def _registration_role_name(user_in: UserRegister) -> str:
    if user_in.role == "student":
        return "student"
    if user_in.apply_for_teacher_review:
        return "pending_teacher"
    return "teacher"


def _get_role(db: Session, role_name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        seed_default_auth_data(db)
        role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise RuntimeError(f"Role {role_name} is not configured.")
    return role


def _load_roles(db: Session, names: list[str]) -> list[Role]:
    unique_names = sorted(set(names))
    if not unique_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one role is required",
        )

    roles = list(db.scalars(select(Role).where(Role.name.in_(unique_names))).all())
    found_names = {role.name for role in roles}
    missing_names = sorted(set(unique_names) - found_names)
    if missing_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role names: {', '.join(missing_names)}",
        )
    return sorted(roles, key=lambda role: role.name)
