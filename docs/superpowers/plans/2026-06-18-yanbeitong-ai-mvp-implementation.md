# Yanbeitong AI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable Yanbeitong AI teacher-preparation workbench with Vue, FastAPI, SQLite, real-API-first AI generation, Mock fallback, lightweight knowledge retrieval, RBAC, versioning, compliance checks, and DOCX export.

**Architecture:** Use a modular monolith: one FastAPI backend split by business domain and one Vue frontend focused on the teacher workbench. Backend modules communicate through Python services and SQLAlchemy models; files live under `data/uploads` and `data/exports`, with SQLite storing metadata and business records.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic, PyJWT/passlib, httpx, python-docx, pypdf, python-pptx, Vue 3, Vite, TypeScript, Pinia, Vue Router, Vitest, pytest.

---

## File Structure

Create this structure from the empty repository:

```text
backend/
  app/
    main.py
    core/
      config.py
      database.py
      security.py
      deps.py
      errors.py
    auth/
      models.py
      schemas.py
      service.py
      router.py
      permissions.py
    ai/
      schemas.py
      service.py
      mock.py
      prompts.py
    compliance/
      models.py
      schemas.py
      service.py
      router.py
    materials/
      models.py
      schemas.py
      parsers.py
      service.py
      router.py
    retrieval/
      schemas.py
      service.py
      router.py
    lessons/
      models.py
      schemas.py
      service.py
      router.py
    exercises/
      models.py
      schemas.py
      service.py
      router.py
    exports/
      schemas.py
      service.py
      router.py
    logs/
      models.py
      schemas.py
      service.py
      router.py
  tests/
    conftest.py
    test_health.py
    test_auth.py
    test_ai.py
    test_compliance.py
    test_materials_retrieval.py
    test_lessons.py
    test_exercises_exports.py
  requirements.txt
  pytest.ini
  .env.example
frontend/
  src/
    main.ts
    App.vue
    router.ts
    api/client.ts
    stores/auth.ts
    layouts/WorkbenchLayout.vue
    pages/LoginPage.vue
    pages/RegisterPage.vue
    pages/DashboardPage.vue
    pages/LessonPage.vue
    pages/ExercisePage.vue
    pages/MaterialsPage.vue
    pages/CompliancePage.vue
    pages/ResourcesPage.vue
    pages/AdminPage.vue
  package.json
  vite.config.ts
  tsconfig.json
```

## Task 1: Backend Project Skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/.env.example`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing health test**

Create `backend/tests/test_health.py`:

```python
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "yanbeitong-ai"}
```

- [ ] **Step 2: Create test client fixture**

Create `backend/tests/conftest.py`:

```python
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


def test_client():
    return TestClient(app)


import pytest  # noqa: E402


@pytest.fixture()
def client():
    with test_client() as c:
        yield c
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 4: Add backend dependencies**

Create `backend/requirements.txt`:

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pydantic-settings==2.7.1
python-multipart==0.0.20
httpx==0.28.1
PyJWT==2.10.1
passlib[bcrypt]==1.7.4
email-validator==2.2.0
python-docx==1.1.2
pypdf==5.1.0
python-pptx==1.0.2
pytest==8.3.4
```

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

Create `backend/.env.example`:

```env
APP_NAME=yanbeitong-ai
DATABASE_URL=sqlite:///../data/app.db
JWT_SECRET=change-me-in-local-env
JWT_EXPIRE_MINUTES=1440
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_API_KEY=
LLM_MODEL=mimo-v2.5-pro
LLM_TIMEOUT_SECONDS=60
LLM_MOCK_ON_FAILURE=true
UPLOAD_DIR=../data/uploads
EXPORT_DIR=../data/exports
```

- [ ] **Step 5: Add config and database helpers**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "yanbeitong-ai"
    database_url: str = "sqlite:///../data/app.db"
    jwt_secret: str = "change-me-in-local-env"
    jwt_expire_minutes: int = 1440
    llm_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    llm_api_key: str = ""
    llm_model: str = "mimo-v2.5-pro"
    llm_timeout_seconds: int = 60
    llm_mock_on_failure: bool = True
    upload_dir: Path = Path("../data/uploads")
    export_dir: Path = Path("../data/exports")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings
```

Create `backend/app/core/database.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Create `backend/app/core/errors.py`:

```python
from fastapi import HTTPException, status


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def forbidden(message: str = "permission denied") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
```

- [ ] **Step 6: Add FastAPI app**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="研备通 AI", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 7: Run test to verify it passes**

Run:

```powershell
cd backend
python -m pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend .gitignore
git commit -m "feat: scaffold backend app"
```

## Task 2: Database Models, RBAC, and Auth

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/deps.py`
- Create: `backend/app/auth/models.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/permissions.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/logs/models.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write auth tests**

Create `backend/tests/test_auth.py`:

```python
def test_register_login_and_me(client):
    register = client.post(
        "/api/auth/register",
        json={
            "username": "teacher1",
            "email": "teacher1@example.com",
            "password": "pass123456",
            "display_name": "Teacher One",
        },
    )
    assert register.status_code == 201
    assert register.json()["username"] == "teacher1"

    login = client.post(
        "/api/auth/login",
        json={"username": "teacher1", "password": "pass123456"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "teacher1"
    assert "teacher" in body["roles"]


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "teacher2",
            "email": "teacher2@example.com",
            "password": "pass123456",
            "display_name": "Teacher Two",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"username": "teacher2", "password": "wrong-pass"},
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_auth.py -v
```

Expected: FAIL with 404 for `/api/auth/register`.

- [ ] **Step 3: Add security helpers**

Create `backend/app/core/security.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
```

- [ ] **Step 4: Add auth and log models**

Create `backend/app/auth/models.py`:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    mapped_column("user_id", ForeignKey("users.id"), primary_key=True),
    mapped_column("role_id", ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    mapped_column("role_id", ForeignKey("roles.id"), primary_key=True),
    mapped_column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255), default="")
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    module: Mapped[str] = mapped_column(String(64))
    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )
```

Create `backend/app/logs/models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelLog(Base):
    __tablename__ = "model_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(default=True)
    fallback_used: Mapped[bool] = mapped_column(default=False)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Add schemas and permissions seed**

Create `backend/app/auth/schemas.py`:

```python
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    roles: list[str]
    permissions: list[str]
```

Create `backend/app/auth/permissions.py`:

```python
DEFAULT_PERMISSIONS = [
    ("lesson:create", "Create lessons", "lesson"),
    ("lesson:export", "Export lessons", "lesson"),
    ("exercise:create", "Create exercises", "exercise"),
    ("material:upload", "Upload materials", "material"),
    ("admin:user_manage", "Manage users", "admin"),
    ("admin:role_manage", "Manage roles", "admin"),
    ("log:view", "View logs", "log"),
]

DEFAULT_ROLES = {
    "admin": [
        "lesson:create",
        "lesson:export",
        "exercise:create",
        "material:upload",
        "admin:user_manage",
        "admin:role_manage",
        "log:view",
    ],
    "teaching_manager": [
        "lesson:create",
        "lesson:export",
        "exercise:create",
        "material:upload",
        "log:view",
    ],
    "teacher": ["lesson:create", "lesson:export", "exercise:create", "material:upload"],
    "operator": ["material:upload"],
}
```

- [ ] **Step 6: Implement auth service and dependencies**

Create `backend/app/auth/service.py`:

```python
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Permission, Role, User
from app.auth.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.auth.schemas import RegisterRequest
from app.core.security import hash_password, verify_password


def seed_rbac(db: Session) -> None:
    permissions_by_code: dict[str, Permission] = {}
    for code, name, module in DEFAULT_PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, name=name, module=module)
            db.add(permission)
        permissions_by_code[code] = permission
    for role_code, permission_codes in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            role = Role(code=role_code, name=role_code.replace("_", " ").title())
            db.add(role)
        role.permissions = [permissions_by_code[code] for code in permission_codes]
    db.commit()


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing:
        raise HTTPException(status_code=409, detail="username already exists")
    seed_rbac(db)
    teacher_role = db.scalar(select(Role).where(Role.code == "teacher"))
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        roles=[teacher_role] if teacher_role else [],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return user


def role_codes(user: User) -> list[str]:
    return [role.code for role in user.roles]


def permission_codes(user: User) -> list[str]:
    codes: set[str] = set()
    for role in user.roles:
        codes.update(permission.code for permission in role.permissions)
    return sorted(codes)
```

Create `backend/app/core/deps.py`:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import permission_codes
from app.core.database import get_db
from app.core.security import decode_access_token

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    user_id = int(payload["sub"])
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def require_permission(code: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if code not in permission_codes(user):
            raise HTTPException(status_code=403, detail="permission denied")
        return user

    return dependency
```

- [ ] **Step 7: Add auth router**

Create `backend/app/auth/router.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.auth.service import authenticate_user, permission_codes, register_user, role_codes
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.auth.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        roles=role_codes(user),
        permissions=permission_codes(user),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    return to_user_response(register_user(db, payload))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    token = create_access_token(str(user.id), {"roles": role_codes(user)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return to_user_response(user)
```

- [ ] **Step 8: Wire metadata and router in main**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.auth import models as auth_models  # noqa: F401
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.logs import models as log_models  # noqa: F401

settings = get_settings()
app = FastAPI(title="研备通 AI", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth_router)
```

- [ ] **Step 9: Run auth tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auth.py tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
git add backend
git commit -m "feat: add authentication and rbac"
```

## Task 3: AI Provider and Compliance

**Files:**
- Create: `backend/app/ai/schemas.py`
- Create: `backend/app/ai/mock.py`
- Create: `backend/app/ai/prompts.py`
- Create: `backend/app/ai/service.py`
- Create: `backend/app/compliance/models.py`
- Create: `backend/app/compliance/schemas.py`
- Create: `backend/app/compliance/service.py`
- Create: `backend/app/compliance/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai.py`
- Test: `backend/tests/test_compliance.py`

- [ ] **Step 1: Write AI and compliance tests**

Create `backend/tests/test_ai.py`:

```python
from app.ai.service import generate_text


def test_ai_uses_mock_when_key_missing(db_session):
    result = generate_text(
        db=db_session,
        task_type="lesson",
        prompt="生成一份考研英语二小作文强化课教案",
    )
    assert result.provider in {"mock", "real"}
    assert result.content
    if result.provider == "mock":
        assert result.fallback_used is True
```

Create `backend/tests/test_compliance.py`:

```python
def test_compliance_detects_guarantee_risk(client):
    response = client.post(
        "/api/compliance/check",
        json={"content_type": "lesson", "content": "本课程保证上岸，100%通过。"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "high"
    assert "保证上岸" in body["matched_terms"]
    assert "100%通过" in body["matched_terms"]
```

Add `db_session` to `backend/tests/conftest.py`:

```python
@pytest.fixture()
def db_session():
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_ai.py tests/test_compliance.py -v
```

Expected: FAIL because `app.ai` and `/api/compliance/check` do not exist.

- [ ] **Step 3: Add AI schemas, mock, and prompt helpers**

Create `backend/app/ai/schemas.py`:

```python
from pydantic import BaseModel


class AIResult(BaseModel):
    content: str
    provider: str
    model: str
    fallback_used: bool
    error_message: str = ""
```

Create `backend/app/ai/mock.py`:

```python
def mock_generate(task_type: str, prompt: str) -> str:
    if task_type == "exercise":
        return (
            "题目1：请说明考研英语二小作文常见书信格式。\n"
            "答案：包括称呼、正文、结束语和署名。\n"
            "解析：格式题应先保证结构完整，再关注语言表达。"
        )
    return (
        "课程定位：考研英语二小作文强化课。\n"
        "教学目标：掌握常见书信结构、评分关注点和表达模板。\n"
        "重点难点：格式规范、语气得体、内容完整。\n"
        "课堂流程：导入10分钟，格式讲解25分钟，范文拆解25分钟，课堂练习20分钟，总结10分钟。\n"
        "互动问题：让学员判断不同称呼和结尾是否适合正式书信。\n"
        "课后任务：完成一篇建议信并按评分标准自查。"
    )
```

Create `backend/app/ai/prompts.py`:

```python
def build_lesson_prompt(form: dict, references: list[str]) -> str:
    ref_text = "\n\n".join(references) if references else "无"
    return (
        "你是一名成人考研机构教研老师。请生成结构化教案。\n"
        f"课程信息：{form}\n"
        f"参考资料：{ref_text}\n"
        "输出必须包含课程定位、教学目标、重点难点、课堂流程、互动问题、课后任务。"
    )


def build_exercise_prompt(form: dict, references: list[str]) -> str:
    ref_text = "\n\n".join(references) if references else "无"
    return (
        "你是一名成人考研机构教研老师。请生成练习题、答案和解析。\n"
        f"题目要求：{form}\n"
        f"参考资料：{ref_text}\n"
        "输出必须包含题目、答案、解析、易错点。"
    )
```

- [ ] **Step 4: Implement AI service**

Create `backend/app/ai/service.py`:

```python
import time

import httpx
from sqlalchemy.orm import Session

from app.ai.mock import mock_generate
from app.ai.schemas import AIResult
from app.core.config import get_settings
from app.logs.models import ModelLog


def _record_model_log(
    db: Session,
    task_type: str,
    result: AIResult,
    latency_ms: int,
    success: bool,
) -> None:
    db.add(
        ModelLog(
            task_type=task_type,
            provider=result.provider,
            model=result.model,
            latency_ms=latency_ms,
            success=success,
            fallback_used=result.fallback_used,
            error_message=result.error_message,
        )
    )
    db.commit()


def generate_text(db: Session, task_type: str, prompt: str) -> AIResult:
    settings = get_settings()
    started = time.perf_counter()
    if settings.llm_api_key:
        try:
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                },
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = AIResult(
                content=content,
                provider="real",
                model=settings.llm_model,
                fallback_used=False,
            )
            _record_model_log(db, task_type, result, int((time.perf_counter() - started) * 1000), True)
            return result
        except Exception as exc:
            if not settings.llm_mock_on_failure:
                raise
            error_message = str(exc)
    else:
        error_message = "LLM_API_KEY is empty"

    content = mock_generate(task_type, prompt)
    result = AIResult(
        content=content,
        provider="mock",
        model="mock-generator",
        fallback_used=True,
        error_message=error_message,
    )
    _record_model_log(db, task_type, result, int((time.perf_counter() - started) * 1000), True)
    return result
```

- [ ] **Step 5: Add compliance service and router**

Create `backend/app/compliance/models.py`:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64))
    pattern: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(16))
    suggestion: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_type: Mapped[str] = mapped_column(String(64))
    content_id: Mapped[str] = mapped_column(String(64), default="")
    risk_level: Mapped[str] = mapped_column(String(16))
    matched_terms_json: Mapped[str] = mapped_column(Text)
    suggestion_json: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `backend/app/compliance/schemas.py`:

```python
from pydantic import BaseModel


class ComplianceCheckRequest(BaseModel):
    content_type: str
    content: str
    content_id: str = ""


class ComplianceCheckResponse(BaseModel):
    risk_level: str
    matched_terms: list[str]
    suggestions: list[str]
```

Create `backend/app/compliance/service.py`:

```python
import json
import re

from sqlalchemy.orm import Session

from app.compliance.models import ComplianceLog
from app.compliance.schemas import ComplianceCheckResponse

HIGH_RISK_TERMS = ["保证上岸", "100%通过", "必过", "保分", "内部押题", "命题人参与"]
PRIVACY_PATTERNS = [
    (r"1[3-9]\d{9}", "手机号"),
    (r"\b[\w.-]+@[\w.-]+\.\w+\b", "邮箱"),
    (r"\b\d{17}[\dXx]\b", "身份证号"),
]


def check_content(db: Session, content_type: str, content: str, content_id: str = "") -> ComplianceCheckResponse:
    matched: list[str] = []
    suggestions: list[str] = []
    for term in HIGH_RISK_TERMS:
        if term in content:
            matched.append(term)
            suggestions.append(f"删除或改写高风险承诺：{term}")
    for pattern, label in PRIVACY_PATTERNS:
        if re.search(pattern, content):
            matched.append(label)
            suggestions.append(f"对{label}进行脱敏或移除")
    risk_level = "high" if any(term in HIGH_RISK_TERMS for term in matched) else "medium" if matched else "low"
    db.add(
        ComplianceLog(
            content_type=content_type,
            content_id=content_id,
            risk_level=risk_level,
            matched_terms_json=json.dumps(matched, ensure_ascii=False),
            suggestion_json=json.dumps(suggestions, ensure_ascii=False),
        )
    )
    db.commit()
    return ComplianceCheckResponse(
        risk_level=risk_level,
        matched_terms=matched,
        suggestions=suggestions,
    )
```

Create `backend/app/compliance/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.compliance.schemas import ComplianceCheckRequest, ComplianceCheckResponse
from app.compliance.service import check_content
from app.core.database import get_db

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.post("/check", response_model=ComplianceCheckResponse)
def check(payload: ComplianceCheckRequest, db: Session = Depends(get_db)) -> ComplianceCheckResponse:
    return check_content(db, payload.content_type, payload.content, payload.content_id)
```

- [ ] **Step 6: Wire compliance models and router**

Modify `backend/app/main.py` imports and router setup:

```python
from app.compliance import models as compliance_models  # noqa: F401
from app.compliance.router import router as compliance_router

app.include_router(compliance_router)
```

- [ ] **Step 7: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/test_ai.py tests/test_compliance.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend
git commit -m "feat: add ai provider and compliance checks"
```

## Task 4: Materials Parsing and Lightweight Retrieval

**Files:**
- Create: `backend/app/materials/models.py`
- Create: `backend/app/materials/schemas.py`
- Create: `backend/app/materials/parsers.py`
- Create: `backend/app/materials/service.py`
- Create: `backend/app/materials/router.py`
- Create: `backend/app/retrieval/schemas.py`
- Create: `backend/app/retrieval/service.py`
- Create: `backend/app/retrieval/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_materials_retrieval.py`

- [ ] **Step 1: Write material upload and retrieval test**

Create `backend/tests/test_materials_retrieval.py`:

```python
from io import BytesIO


def test_upload_txt_and_search(client):
    user = client.post(
        "/api/auth/register",
        json={
            "username": "material_user",
            "email": "material_user@example.com",
            "password": "pass123456",
            "display_name": "Material User",
        },
    )
    assert user.status_code == 201
    token = client.post(
        "/api/auth/login",
        json={"username": "material_user", "password": "pass123456"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/materials/upload",
        headers=headers,
        files={"file": ("english.txt", BytesIO("小作文 格式 称呼 正文 结尾".encode("utf-8")), "text/plain")},
        data={"title": "英语小作文讲义"},
    )
    assert response.status_code == 201
    material_id = response.json()["id"]

    search = client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "小作文格式", "top_k": 3, "material_ids": [material_id]},
    )
    assert search.status_code == 200
    body = search.json()
    assert body["chunks"]
    assert body["chunks"][0]["material_id"] == material_id
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_materials_retrieval.py -v
```

Expected: FAIL with 404 for `/api/materials/upload`.

- [ ] **Step 3: Add material models and schemas**

Create `backend/app/materials/models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(String(512))
    uploader_id: Mapped[int] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(32), default="parsed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slide_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    future_vector_id: Mapped[str] = mapped_column(String(128), default="")
    future_embedding_model: Mapped[str] = mapped_column(String(128), default="")
```

Create `backend/app/materials/schemas.py`:

```python
from pydantic import BaseModel


class MaterialResponse(BaseModel):
    id: int
    title: str
    file_name: str
    file_type: str
    parse_status: str
    chunk_count: int


class MaterialChunkResponse(BaseModel):
    id: int
    material_id: int
    content: str
    page_no: int | None = None
    slide_no: int | None = None
    score: float = 0
```

- [ ] **Step 4: Add file parsers**

Create `backend/app/materials/parsers.py`:

```python
from pathlib import Path

from docx import Document
from pptx import Presentation
from pypdf import PdfReader


def parse_text_file(path: Path) -> list[tuple[str, int | None, int | None]]:
    return [(path.read_text(encoding="utf-8", errors="ignore"), None, None)]


def parse_docx(path: Path) -> list[tuple[str, int | None, int | None]]:
    doc = Document(path)
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            texts.append(" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
    return [("\n".join(texts), None, None)]


def parse_pdf(path: Path) -> list[tuple[str, int | None, int | None]]:
    reader = PdfReader(str(path))
    result: list[tuple[str, int | None, int | None]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            result.append((text, index, None))
    return result


def parse_pptx(path: Path) -> list[tuple[str, int | None, int | None]]:
    deck = Presentation(path)
    result: list[tuple[str, int | None, int | None]] = []
    for index, slide in enumerate(deck.slides, start=1):
        texts: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                texts.append(shape.text.strip())
        if texts:
            result.append(("\n".join(texts), None, index))
    return result


def parse_file(path: Path, suffix: str) -> list[tuple[str, int | None, int | None]]:
    suffix = suffix.lower()
    if suffix in {".txt", ".md"}:
        return parse_text_file(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".pptx":
        return parse_pptx(path)
    raise ValueError(f"unsupported file type: {suffix}")
```

- [ ] **Step 5: Add material service and router**

Create `backend/app/materials/service.py`:

```python
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.materials.models import Material, MaterialChunk
from app.materials.parsers import parse_file


def chunk_text(text: str, size: int = 700) -> list[str]:
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) > size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def save_upload(db: Session, file: UploadFile, title: str, uploader_id: int) -> Material:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    target = settings.upload_dir / f"{uuid4().hex}{suffix}"
    target.write_bytes(file.file.read())
    material = Material(
        title=title,
        file_name=file.filename or target.name,
        file_type=suffix.lstrip("."),
        file_path=str(target),
        uploader_id=uploader_id,
        parse_status="parsed",
    )
    db.add(material)
    db.flush()
    parsed = parse_file(target, suffix)
    index = 0
    for text, page_no, slide_no in parsed:
        for chunk in chunk_text(text):
            db.add(
                MaterialChunk(
                    material_id=material.id,
                    chunk_index=index,
                    content=chunk,
                    page_no=page_no,
                    slide_no=slide_no,
                    token_count=len(chunk),
                )
            )
            index += 1
    if index == 0:
        material.parse_status = "empty"
    db.commit()
    db.refresh(material)
    return material


def chunk_count(db: Session, material_id: int) -> int:
    return db.scalar(select(func.count()).select_from(MaterialChunk).where(MaterialChunk.material_id == material_id)) or 0
```

Create `backend/app/materials/router.py`:

```python
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.materials.schemas import MaterialResponse
from app.materials.service import chunk_count, save_upload

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=MaterialResponse)
def upload_material(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("material:upload")),
) -> MaterialResponse:
    material = save_upload(db, file, title, user.id)
    return MaterialResponse(
        id=material.id,
        title=material.title,
        file_name=material.file_name,
        file_type=material.file_type,
        parse_status=material.parse_status,
        chunk_count=chunk_count(db, material.id),
    )
```

- [ ] **Step 6: Add retrieval service and router**

Create `backend/app/retrieval/schemas.py`:

```python
from pydantic import BaseModel, Field

from app.materials.schemas import MaterialChunkResponse


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 5
    material_ids: list[int] = []


class RetrievalResponse(BaseModel):
    chunks: list[MaterialChunkResponse]
```

Create `backend/app/retrieval/service.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.materials.models import MaterialChunk
from app.materials.schemas import MaterialChunkResponse


def score_chunk(query: str, content: str) -> float:
    query_terms = [term for term in query.lower().split() if term]
    if not query_terms:
        query_terms = list(query.lower())
    content_lower = content.lower()
    hits = sum(1 for term in query_terms if term in content_lower)
    return hits / max(len(query_terms), 1)


def search_chunks(db: Session, query: str, top_k: int, material_ids: list[int]) -> list[MaterialChunkResponse]:
    stmt = select(MaterialChunk)
    if material_ids:
        stmt = stmt.where(MaterialChunk.material_id.in_(material_ids))
    scored: list[tuple[float, MaterialChunk]] = []
    for chunk in db.scalars(stmt).all():
        score = score_chunk(query, chunk.content)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        MaterialChunkResponse(
            id=chunk.id,
            material_id=chunk.material_id,
            content=chunk.content,
            page_no=chunk.page_no,
            slide_no=chunk.slide_no,
            score=score,
        )
        for score, chunk in scored[:top_k]
    ]
```

Create `backend/app/retrieval/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.retrieval.schemas import RetrievalRequest, RetrievalResponse
from app.retrieval.service import search_chunks

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
def search(payload: RetrievalRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)) -> RetrievalResponse:
    return RetrievalResponse(chunks=search_chunks(db, payload.query, payload.top_k, payload.material_ids))
```

- [ ] **Step 7: Wire material and retrieval modules**

Modify `backend/app/main.py`:

```python
from app.materials import models as material_models  # noqa: F401
from app.materials.router import router as materials_router
from app.retrieval.router import router as retrieval_router

app.include_router(materials_router)
app.include_router(retrieval_router)
```

- [ ] **Step 8: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/test_materials_retrieval.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add backend
git commit -m "feat: add materials parsing and retrieval"
```

## Task 5: Lessons and Versioning

**Files:**
- Create: `backend/app/lessons/models.py`
- Create: `backend/app/lessons/schemas.py`
- Create: `backend/app/lessons/service.py`
- Create: `backend/app/lessons/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_lessons.py`

- [ ] **Step 1: Write lesson flow test**

Create `backend/tests/test_lessons.py`:

```python
def auth_headers(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "lesson_user",
            "email": "lesson_user@example.com",
            "password": "pass123456",
            "display_name": "Lesson User",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"username": "lesson_user", "password": "pass123456"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_save_and_restore_lesson(client):
    headers = auth_headers(client)
    generated = client.post(
        "/api/lessons/generate",
        headers=headers,
        json={
            "subject": "考研英语二",
            "chapter": "小作文",
            "stage": "强化",
            "duration_minutes": 90,
            "student_level": "基础一般",
            "teaching_goal": "掌握书信格式",
            "use_materials": False,
            "material_ids": [],
        },
    )
    assert generated.status_code == 200
    content = generated.json()["content"]
    assert "教学目标" in content

    saved = client.post(
        "/api/lessons",
        headers=headers,
        json={
            "title": "英语二小作文强化课",
            "subject": "考研英语二",
            "chapter": "小作文",
            "stage": "强化",
            "duration_minutes": 90,
            "student_level": "基础一般",
            "content": content,
            "change_note": "初稿",
        },
    )
    assert saved.status_code == 201
    lesson_id = saved.json()["id"]

    versions = client.get(f"/api/lessons/{lesson_id}/versions", headers=headers)
    assert versions.status_code == 200
    assert versions.json()[0]["version_no"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_lessons.py -v
```

Expected: FAIL with 404 for `/api/lessons/generate`.

- [ ] **Step 3: Add lesson models and schemas**

Create `backend/app/lessons/models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128))
    chapter: Mapped[str] = mapped_column(String(128))
    stage: Mapped[str] = mapped_column(String(64))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    student_level: Mapped[str] = mapped_column(String(128))
    current_content: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(Integer)
    compliance_level: Mapped[str] = mapped_column(String(16), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LessonVersion(Base):
    __tablename__ = "lesson_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(Integer, index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    change_note: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `backend/app/lessons/schemas.py`:

```python
from pydantic import BaseModel


class LessonGenerateRequest(BaseModel):
    subject: str
    chapter: str
    stage: str
    duration_minutes: int
    student_level: str
    teaching_goal: str
    use_materials: bool = False
    material_ids: list[int] = []


class LessonGenerateResponse(BaseModel):
    content: str
    references: list[str]
    provider_status: dict
    compliance: dict


class LessonCreateRequest(BaseModel):
    title: str
    subject: str
    chapter: str
    stage: str
    duration_minutes: int
    student_level: str
    content: str
    change_note: str = "保存版本"


class LessonResponse(BaseModel):
    id: int
    title: str
    subject: str
    chapter: str
    stage: str
    duration_minutes: int
    student_level: str
    current_content: str
    compliance_level: str


class LessonVersionResponse(BaseModel):
    id: int
    lesson_id: int
    version_no: int
    content: str
    change_note: str
```

- [ ] **Step 4: Add lesson service and router**

Create `backend/app/lessons/service.py`:

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.prompts import build_lesson_prompt
from app.ai.service import generate_text
from app.compliance.service import check_content
from app.lessons.models import Lesson, LessonVersion
from app.lessons.schemas import LessonCreateRequest, LessonGenerateRequest
from app.retrieval.service import search_chunks


def generate_lesson(db: Session, payload: LessonGenerateRequest) -> tuple[str, list[str], dict, dict]:
    references = []
    if payload.use_materials:
        chunks = search_chunks(db, f"{payload.subject} {payload.chapter} {payload.teaching_goal}", 5, payload.material_ids)
        references = [chunk.content for chunk in chunks]
    prompt = build_lesson_prompt(payload.model_dump(), references)
    ai_result = generate_text(db, "lesson", prompt)
    compliance = check_content(db, "lesson", ai_result.content)
    return ai_result.content, references, ai_result.model_dump(), compliance.model_dump()


def create_lesson(db: Session, payload: LessonCreateRequest, owner_id: int) -> Lesson:
    compliance = check_content(db, "lesson", payload.content)
    lesson = Lesson(
        title=payload.title,
        subject=payload.subject,
        chapter=payload.chapter,
        stage=payload.stage,
        duration_minutes=payload.duration_minutes,
        student_level=payload.student_level,
        current_content=payload.content,
        owner_id=owner_id,
        compliance_level=compliance.risk_level,
    )
    db.add(lesson)
    db.flush()
    db.add(
        LessonVersion(
            lesson_id=lesson.id,
            version_no=1,
            content=payload.content,
            change_note=payload.change_note,
            created_by=owner_id,
        )
    )
    db.commit()
    db.refresh(lesson)
    return lesson


def list_versions(db: Session, lesson_id: int) -> list[LessonVersion]:
    return list(db.scalars(select(LessonVersion).where(LessonVersion.lesson_id == lesson_id).order_by(LessonVersion.version_no)))
```

Create `backend/app/lessons/router.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.lessons.schemas import (
    LessonCreateRequest,
    LessonGenerateRequest,
    LessonGenerateResponse,
    LessonResponse,
    LessonVersionResponse,
)
from app.lessons.service import create_lesson, generate_lesson, list_versions

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.post("/generate", response_model=LessonGenerateResponse)
def generate(
    payload: LessonGenerateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("lesson:create")),
) -> LessonGenerateResponse:
    content, references, provider_status, compliance = generate_lesson(db, payload)
    return LessonGenerateResponse(
        content=content,
        references=references,
        provider_status=provider_status,
        compliance=compliance,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LessonResponse)
def create(
    payload: LessonCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("lesson:create")),
) -> LessonResponse:
    lesson = create_lesson(db, payload, user.id)
    return LessonResponse(
        id=lesson.id,
        title=lesson.title,
        subject=lesson.subject,
        chapter=lesson.chapter,
        stage=lesson.stage,
        duration_minutes=lesson.duration_minutes,
        student_level=lesson.student_level,
        current_content=lesson.current_content,
        compliance_level=lesson.compliance_level,
    )


@router.get("/{lesson_id}/versions", response_model=list[LessonVersionResponse])
def versions(
    lesson_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("lesson:create")),
) -> list[LessonVersionResponse]:
    return [
        LessonVersionResponse(
            id=version.id,
            lesson_id=version.lesson_id,
            version_no=version.version_no,
            content=version.content,
            change_note=version.change_note,
        )
        for version in list_versions(db, lesson_id)
    ]
```

- [ ] **Step 5: Wire lesson module**

Modify `backend/app/main.py`:

```python
from app.lessons import models as lesson_models  # noqa: F401
from app.lessons.router import router as lessons_router

app.include_router(lessons_router)
```

- [ ] **Step 6: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/test_lessons.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend
git commit -m "feat: add lesson generation and versioning"
```

## Task 6: Exercises and DOCX Exports

**Files:**
- Create: `backend/app/exercises/models.py`
- Create: `backend/app/exercises/schemas.py`
- Create: `backend/app/exercises/service.py`
- Create: `backend/app/exercises/router.py`
- Create: `backend/app/exports/schemas.py`
- Create: `backend/app/exports/service.py`
- Create: `backend/app/exports/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_exercises_exports.py`

- [ ] **Step 1: Write exercise and export tests**

Create `backend/tests/test_exercises_exports.py`:

```python
def login_headers(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "exercise_user",
            "email": "exercise_user@example.com",
            "password": "pass123456",
            "display_name": "Exercise User",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"username": "exercise_user", "password": "pass123456"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_save_and_export_exercise_docx(client):
    headers = login_headers(client)
    generated = client.post(
        "/api/exercises/generate",
        headers=headers,
        json={
            "title": "矩阵秩基础题",
            "subject": "考研数学",
            "knowledge_point": "矩阵秩",
            "question_type": "选择题",
            "difficulty": "基础",
            "count": 3,
            "use_materials": False,
            "material_ids": [],
        },
    )
    assert generated.status_code == 200
    content = generated.json()["content"]
    assert "答案" in content

    saved = client.post(
        "/api/exercises",
        headers=headers,
        json={
            "title": "矩阵秩基础题",
            "subject": "考研数学",
            "knowledge_point": "矩阵秩",
            "question_type": "选择题",
            "difficulty": "基础",
            "content": content,
            "change_note": "初稿",
        },
    )
    assert saved.status_code == 201
    exercise_id = saved.json()["id"]

    exported = client.post(f"/api/exports/exercise/{exercise_id}/docx", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["file_path"].endswith(".docx")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_exercises_exports.py -v
```

Expected: FAIL with 404 for `/api/exercises/generate`.

- [ ] **Step 3: Add exercise models and schemas**

Create `backend/app/exercises/models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128))
    knowledge_point: Mapped[str] = mapped_column(String(128))
    question_type: Mapped[str] = mapped_column(String(64))
    difficulty: Mapped[str] = mapped_column(String(64))
    current_content_json: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(Integer)
    compliance_level: Mapped[str] = mapped_column(String(16), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExerciseVersion(Base):
    __tablename__ = "exercise_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(Integer, index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[str] = mapped_column(Text)
    change_note: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `backend/app/exercises/schemas.py`:

```python
from pydantic import BaseModel


class ExerciseGenerateRequest(BaseModel):
    title: str
    subject: str
    knowledge_point: str
    question_type: str
    difficulty: str
    count: int
    use_materials: bool = False
    material_ids: list[int] = []


class ExerciseGenerateResponse(BaseModel):
    content: str
    references: list[str]
    provider_status: dict
    compliance: dict


class ExerciseCreateRequest(BaseModel):
    title: str
    subject: str
    knowledge_point: str
    question_type: str
    difficulty: str
    content: str
    change_note: str = "保存版本"


class ExerciseResponse(BaseModel):
    id: int
    title: str
    subject: str
    knowledge_point: str
    question_type: str
    difficulty: str
    current_content_json: str
    compliance_level: str
```

- [ ] **Step 4: Add exercise service and router**

Create `backend/app/exercises/service.py`:

```python
from sqlalchemy.orm import Session

from app.ai.prompts import build_exercise_prompt
from app.ai.service import generate_text
from app.compliance.service import check_content
from app.exercises.models import Exercise, ExerciseVersion
from app.exercises.schemas import ExerciseCreateRequest, ExerciseGenerateRequest
from app.retrieval.service import search_chunks


def generate_exercise(db: Session, payload: ExerciseGenerateRequest) -> tuple[str, list[str], dict, dict]:
    references = []
    if payload.use_materials:
        chunks = search_chunks(db, f"{payload.subject} {payload.knowledge_point}", 5, payload.material_ids)
        references = [chunk.content for chunk in chunks]
    prompt = build_exercise_prompt(payload.model_dump(), references)
    ai_result = generate_text(db, "exercise", prompt)
    compliance = check_content(db, "exercise", ai_result.content)
    return ai_result.content, references, ai_result.model_dump(), compliance.model_dump()


def create_exercise(db: Session, payload: ExerciseCreateRequest, owner_id: int) -> Exercise:
    compliance = check_content(db, "exercise", payload.content)
    exercise = Exercise(
        title=payload.title,
        subject=payload.subject,
        knowledge_point=payload.knowledge_point,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        current_content_json=payload.content,
        owner_id=owner_id,
        compliance_level=compliance.risk_level,
    )
    db.add(exercise)
    db.flush()
    db.add(
        ExerciseVersion(
            exercise_id=exercise.id,
            version_no=1,
            content_json=payload.content,
            change_note=payload.change_note,
            created_by=owner_id,
        )
    )
    db.commit()
    db.refresh(exercise)
    return exercise
```

Create `backend/app/exercises/router.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.exercises.schemas import (
    ExerciseCreateRequest,
    ExerciseGenerateRequest,
    ExerciseGenerateResponse,
    ExerciseResponse,
)
from app.exercises.service import create_exercise, generate_exercise

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.post("/generate", response_model=ExerciseGenerateResponse)
def generate(
    payload: ExerciseGenerateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("exercise:create")),
) -> ExerciseGenerateResponse:
    content, references, provider_status, compliance = generate_exercise(db, payload)
    return ExerciseGenerateResponse(
        content=content,
        references=references,
        provider_status=provider_status,
        compliance=compliance,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ExerciseResponse)
def create(
    payload: ExerciseCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("exercise:create")),
) -> ExerciseResponse:
    exercise = create_exercise(db, payload, user.id)
    return ExerciseResponse(
        id=exercise.id,
        title=exercise.title,
        subject=exercise.subject,
        knowledge_point=exercise.knowledge_point,
        question_type=exercise.question_type,
        difficulty=exercise.difficulty,
        current_content_json=exercise.current_content_json,
        compliance_level=exercise.compliance_level,
    )
```

- [ ] **Step 5: Add DOCX export service**

Create `backend/app/exports/schemas.py`:

```python
from pydantic import BaseModel


class ExportResponse(BaseModel):
    file_path: str
```

Create `backend/app/exports/service.py`:

```python
from pathlib import Path

from docx import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.exercises.models import Exercise
from app.lessons.models import Lesson


def export_lesson_docx(db: Session, lesson_id: int) -> Path:
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id))
    if lesson is None:
        raise ValueError("lesson not found")
    target = get_settings().export_dir / f"lesson-{lesson.id}.docx"
    doc = Document()
    doc.add_heading(lesson.title, level=1)
    doc.add_paragraph(f"科目：{lesson.subject}")
    doc.add_paragraph(f"章节：{lesson.chapter}")
    doc.add_paragraph(f"阶段：{lesson.stage}")
    doc.add_heading("教案内容", level=2)
    for line in lesson.current_content.splitlines():
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.add_paragraph(f"合规风险等级：{lesson.compliance_level}")
    doc.save(target)
    return target


def export_exercise_docx(db: Session, exercise_id: int) -> Path:
    exercise = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
    if exercise is None:
        raise ValueError("exercise not found")
    target = get_settings().export_dir / f"exercise-{exercise.id}.docx"
    doc = Document()
    doc.add_heading(exercise.title, level=1)
    doc.add_paragraph(f"科目：{exercise.subject}")
    doc.add_paragraph(f"知识点：{exercise.knowledge_point}")
    doc.add_paragraph(f"题型：{exercise.question_type}")
    doc.add_heading("习题内容", level=2)
    for line in exercise.current_content_json.splitlines():
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.add_paragraph(f"合规风险等级：{exercise.compliance_level}")
    doc.save(target)
    return target
```

Create `backend/app/exports/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.exports.schemas import ExportResponse
from app.exports.service import export_exercise_docx, export_lesson_docx

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("/lesson/{lesson_id}/docx", response_model=ExportResponse)
def export_lesson(lesson_id: int, db: Session = Depends(get_db), _user=Depends(require_permission("lesson:export"))) -> ExportResponse:
    return ExportResponse(file_path=str(export_lesson_docx(db, lesson_id)))


@router.post("/exercise/{exercise_id}/docx", response_model=ExportResponse)
def export_exercise(exercise_id: int, db: Session = Depends(get_db), _user=Depends(require_permission("lesson:export"))) -> ExportResponse:
    return ExportResponse(file_path=str(export_exercise_docx(db, exercise_id)))
```

- [ ] **Step 6: Wire exercise and export modules**

Modify `backend/app/main.py`:

```python
from app.exercises import models as exercise_models  # noqa: F401
from app.exercises.router import router as exercises_router
from app.exports.router import router as exports_router

app.include_router(exercises_router)
app.include_router(exports_router)
```

- [ ] **Step 7: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/test_exercises_exports.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend
git commit -m "feat: add exercises and docx exports"
```

## Task 7: Frontend Scaffold and Auth Flow

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/pages/LoginPage.vue`
- Create: `frontend/src/pages/RegisterPage.vue`

- [ ] **Step 1: Create package and Vite config**

Create `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "pinia": "^2.3.0",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "typescript": "^5.7.2",
    "vite": "^6.0.5",
    "vitest": "^2.1.8",
    "vue-tsc": "^2.2.0"
  }
}
```

Create `frontend/vite.config.ts`:

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "strict": true,
    "jsx": "preserve",
    "sourceMap": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "lib": ["ES2020", "DOM"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue"]
}
```

- [ ] **Step 2: Add Vue entry and router**

Create `frontend/index.html`:

```html
<div id="app"></div>
<script type="module" src="/src/main.ts"></script>
```

Create `frontend/src/main.ts`:

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

createApp(App).use(createPinia()).use(router).mount('#app')
```

Create `frontend/src/App.vue`:

```vue
<template>
  <router-view />
</template>
```

Create `frontend/src/router.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from './pages/LoginPage.vue'
import RegisterPage from './pages/RegisterPage.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
  ],
})
```

- [ ] **Step 3: Add API client and auth store**

Create `frontend/src/api/client.ts`:

```ts
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...options, headers })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}
```

Create `frontend/src/stores/auth.ts`:

```ts
import { defineStore } from 'pinia'
import { api } from '../api/client'

type User = {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: localStorage.getItem('token') || '',
  }),
  actions: {
    async login(username: string, password: string) {
      const token = await api<{ access_token: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      this.token = token.access_token
      localStorage.setItem('token', token.access_token)
      this.user = await api<User>('/api/auth/me')
    },
    async register(username: string, email: string, password: string, display_name: string) {
      await api<User>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, email, password, display_name }),
      })
      await this.login(username, password)
    },
  },
})
```

- [ ] **Step 4: Add login and register pages**

Create `frontend/src/pages/LoginPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    await router.push('/dashboard')
  } catch (err) {
    error.value = String(err)
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="panel">
      <h1>研备通 AI</h1>
      <p>成人考研机构智能备课工作台</p>
      <input v-model="username" placeholder="用户名" />
      <input v-model="password" placeholder="密码" type="password" />
      <button @click="submit">登录</button>
      <router-link to="/register">注册新账号</router-link>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </main>
</template>

<style scoped>
.auth-page { min-height: 100vh; display: grid; place-items: center; background: #f4f6f9; }
.panel { width: 360px; padding: 28px; background: white; border: 1px solid #dde3ee; border-radius: 8px; }
input, button { width: 100%; box-sizing: border-box; margin-top: 12px; padding: 10px; }
button { background: #2563eb; color: white; border: 0; border-radius: 6px; }
.error { color: #b42318; }
</style>
```

Create `frontend/src/pages/RegisterPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const email = ref('')
const displayName = ref('')
const password = ref('')
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  try {
    await auth.register(username.value, email.value, password.value, displayName.value)
    await router.push('/dashboard')
  } catch (err) {
    error.value = String(err)
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="panel">
      <h1>注册账号</h1>
      <p>新账号默认授予教师角色，管理员可调整权限。</p>
      <input v-model="username" placeholder="用户名" />
      <input v-model="email" placeholder="邮箱" />
      <input v-model="displayName" placeholder="显示名称" />
      <input v-model="password" placeholder="密码" type="password" />
      <button @click="submit">注册并进入</button>
      <router-link to="/login">返回登录</router-link>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </main>
</template>

<style scoped>
.auth-page { min-height: 100vh; display: grid; place-items: center; background: #f4f6f9; }
.panel { width: 380px; padding: 28px; background: white; border: 1px solid #dde3ee; border-radius: 8px; }
input, button { width: 100%; box-sizing: border-box; margin-top: 12px; padding: 10px; }
button { background: #2563eb; color: white; border: 0; border-radius: 6px; }
.error { color: #b42318; }
</style>
```

- [ ] **Step 5: Run frontend build**

Run:

```powershell
cd frontend
npm install
npm run build
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```powershell
git add frontend
git commit -m "feat: scaffold frontend auth flow"
```

## Task 8: Frontend Workbench Pages

**Files:**
- Create: `frontend/src/layouts/WorkbenchLayout.vue`
- Create: `frontend/src/pages/DashboardPage.vue`
- Create: `frontend/src/pages/LessonPage.vue`
- Create: `frontend/src/pages/ExercisePage.vue`
- Create: `frontend/src/pages/MaterialsPage.vue`
- Create: `frontend/src/pages/CompliancePage.vue`
- Create: `frontend/src/pages/ResourcesPage.vue`
- Create: `frontend/src/pages/AdminPage.vue`
- Modify: `frontend/src/router.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add multipart helper to API client**

Modify `frontend/src/api/client.ts`:

```ts
export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const token = localStorage.getItem('token')
  const headers = new Headers()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { method: 'POST', headers, body: form })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}
```

- [ ] **Step 2: Add workbench layout**

Create `frontend/src/layouts/WorkbenchLayout.vue`:

```vue
<template>
  <div class="layout">
    <aside>
      <h2>研备通 AI</h2>
      <router-link to="/dashboard">工作台</router-link>
      <router-link to="/lessons">新建备课</router-link>
      <router-link to="/exercises">习题生成</router-link>
      <router-link to="/materials">机构知识库</router-link>
      <router-link to="/compliance">合规审核</router-link>
      <router-link to="/resources">资源库</router-link>
      <router-link to="/admin">系统管理</router-link>
    </aside>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout { min-height: 100vh; display: grid; grid-template-columns: 220px 1fr; background: #f6f7fb; }
aside { background: #111827; color: white; padding: 18px; display: flex; flex-direction: column; gap: 10px; }
a { color: #dbeafe; text-decoration: none; padding: 8px; border-radius: 6px; }
a.router-link-active { background: #2563eb; color: white; }
main { padding: 24px; }
</style>
```

- [ ] **Step 3: Add dashboard page**

Create `frontend/src/pages/DashboardPage.vue`:

```vue
<template>
  <section class="page">
    <h1>教师工作台</h1>
    <div class="grid">
      <article><h3>新建备课</h3><p>填写课程信息，生成教案并保存版本。</p></article>
      <article><h3>机构知识库</h3><p>上传讲义、PPT、PDF，生成时引用资料片段。</p></article>
      <article><h3>模型状态</h3><p>真实 API 优先，失败时 Mock 兜底。</p></article>
    </div>
  </section>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
article { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
</style>
```

- [ ] **Step 4: Add lesson page**

Create `frontend/src/pages/LessonPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const form = ref({
  subject: '考研英语二',
  chapter: '小作文',
  stage: '强化',
  duration_minutes: 90,
  student_level: '基础一般',
  teaching_goal: '掌握书信格式',
  use_materials: false,
  material_ids: [] as number[],
})
const content = ref('')
const status = ref('')

async function generate() {
  const result = await api<{ content: string; provider_status: Record<string, unknown> }>('/api/lessons/generate', {
    method: 'POST',
    body: JSON.stringify(form.value),
  })
  content.value = result.content
  status.value = JSON.stringify(result.provider_status)
}

async function save() {
  await api('/api/lessons', {
    method: 'POST',
    body: JSON.stringify({
      title: `${form.value.subject}${form.value.chapter}${form.value.stage}课`,
      ...form.value,
      content: content.value,
      change_note: '前端保存',
    }),
  })
  alert('已保存')
}
</script>

<template>
  <section>
    <h1>新建备课</h1>
    <div class="form">
      <input v-model="form.subject" />
      <input v-model="form.chapter" />
      <input v-model="form.stage" />
      <input v-model="form.student_level" />
      <textarea v-model="form.teaching_goal" />
      <button @click="generate">生成教案</button>
    </div>
    <p>模型状态：{{ status }}</p>
    <textarea v-model="content" class="editor" />
    <button @click="save">保存版本</button>
  </section>
</template>

<style scoped>
.form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
input, textarea, button { padding: 10px; }
.editor { width: 100%; min-height: 360px; margin-top: 16px; box-sizing: border-box; }
</style>
```

- [ ] **Step 5: Add exercise, materials, compliance, resources, and admin pages**

Create `frontend/src/pages/ExercisePage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const form = ref({
  title: '矩阵秩基础题',
  subject: '考研数学',
  knowledge_point: '矩阵秩',
  question_type: '选择题',
  difficulty: '基础',
  count: 3,
  use_materials: false,
  material_ids: [] as number[],
})
const content = ref('')
const status = ref('')

async function generate() {
  const result = await api<{ content: string; provider_status: Record<string, unknown> }>('/api/exercises/generate', {
    method: 'POST',
    body: JSON.stringify(form.value),
  })
  content.value = result.content
  status.value = JSON.stringify(result.provider_status)
}

async function save() {
  await api('/api/exercises', {
    method: 'POST',
    body: JSON.stringify({ ...form.value, content: content.value, change_note: '前端保存' }),
  })
  alert('习题已保存')
}
</script>

<template>
  <section>
    <h1>习题生成</h1>
    <div class="form">
      <input v-model="form.title" />
      <input v-model="form.subject" />
      <input v-model="form.knowledge_point" />
      <input v-model="form.question_type" />
      <input v-model="form.difficulty" />
      <input v-model.number="form.count" type="number" />
      <button @click="generate">生成习题</button>
    </div>
    <p>模型状态：{{ status }}</p>
    <textarea v-model="content" class="editor" />
    <button @click="save">保存版本</button>
  </section>
</template>

<style scoped>
.form { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
input, textarea, button { padding: 10px; }
.editor { width: 100%; min-height: 320px; margin-top: 16px; box-sizing: border-box; }
</style>
```

Create `frontend/src/pages/MaterialsPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { apiForm } from '../api/client'

const title = ref('英语小作文讲义')
const file = ref<File | null>(null)
const result = ref('')

function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

async function upload() {
  if (!file.value) {
    result.value = '请选择文件'
    return
  }
  const form = new FormData()
  form.append('title', title.value)
  form.append('file', file.value)
  const response = await apiForm<Record<string, unknown>>('/api/materials/upload', form)
  result.value = JSON.stringify(response, null, 2)
}
</script>

<template>
  <section>
    <h1>机构知识库</h1>
    <input v-model="title" placeholder="资料标题" />
    <input type="file" accept=".txt,.md,.docx,.pdf,.pptx" @change="onFile" />
    <button @click="upload">上传并解析</button>
    <pre>{{ result }}</pre>
  </section>
</template>

<style scoped>
input, button { display: block; margin: 10px 0; padding: 10px; }
pre { background: white; border: 1px solid #e5e7eb; padding: 12px; border-radius: 8px; }
</style>
```

Create `frontend/src/pages/CompliancePage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const content = ref('保证上岸，100%通过')
const result = ref('')

async function check() {
  const response = await api<Record<string, unknown>>('/api/compliance/check', {
    method: 'POST',
    body: JSON.stringify({ content_type: 'manual', content: content.value }),
  })
  result.value = JSON.stringify(response, null, 2)
}
</script>

<template>
  <section>
    <h1>合规审核</h1>
    <textarea v-model="content" />
    <button @click="check">检测风险</button>
    <pre>{{ result }}</pre>
  </section>
</template>

<style scoped>
textarea { width: 100%; min-height: 220px; box-sizing: border-box; padding: 10px; }
button { margin: 12px 0; padding: 10px 14px; }
pre { background: white; border: 1px solid #e5e7eb; padding: 12px; border-radius: 8px; }
</style>
```

Create `frontend/src/pages/ResourcesPage.vue`:

```vue
<template>
  <section>
    <h1>资源库</h1>
    <p>第一版资源库聚合教案、习题和资料。后端保存接口完成后，这里展示最近资源、版本历史和恢复入口。</p>
  </section>
</template>
```

Create `frontend/src/pages/AdminPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const roles = ref('')

async function loadRoles() {
  const response = await api<Record<string, unknown>[]>('/api/admin/roles')
  roles.value = JSON.stringify(response, null, 2)
}
</script>

<template>
  <section>
    <h1>系统管理</h1>
    <button @click="loadRoles">加载角色权限</button>
    <pre>{{ roles }}</pre>
  </section>
</template>

<style scoped>
button { padding: 10px 14px; }
pre { background: white; border: 1px solid #e5e7eb; padding: 12px; border-radius: 8px; }
</style>
```

- [ ] **Step 6: Wire routes**

Modify `frontend/src/router.ts`:

```ts
import WorkbenchLayout from './layouts/WorkbenchLayout.vue'
import DashboardPage from './pages/DashboardPage.vue'
import LessonPage from './pages/LessonPage.vue'
import ExercisePage from './pages/ExercisePage.vue'
import MaterialsPage from './pages/MaterialsPage.vue'
import CompliancePage from './pages/CompliancePage.vue'
import ResourcesPage from './pages/ResourcesPage.vue'
import AdminPage from './pages/AdminPage.vue'

// Keep existing auth imports.

const workbenchChildren = [
  { path: '/dashboard', component: DashboardPage },
  { path: '/lessons', component: LessonPage },
  { path: '/exercises', component: ExercisePage },
  { path: '/materials', component: MaterialsPage },
  { path: '/compliance', component: CompliancePage },
  { path: '/resources', component: ResourcesPage },
  { path: '/admin', component: AdminPage },
]

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/', component: WorkbenchLayout, children: workbenchChildren },
  ],
})
```

- [ ] **Step 7: Run build**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add frontend
git commit -m "feat: add teacher workbench pages"
```

## Task 9: Logs, Admin APIs, and Final Verification

**Files:**
- Create: `backend/app/logs/schemas.py`
- Create: `backend/app/logs/router.py`
- Create: `backend/app/auth/admin_router.py`
- Modify: `backend/app/main.py`
- Create: `README.md`

- [ ] **Step 1: Add logs schemas and router**

Create `backend/app/logs/schemas.py`:

```python
from pydantic import BaseModel


class OperationLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str
    detail: str


class ModelLogResponse(BaseModel):
    id: int
    task_type: str
    provider: str
    model: str
    success: bool
    fallback_used: bool
    error_message: str
```

Create `backend/app/logs/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.logs.models import ModelLog, OperationLog
from app.logs.schemas import ModelLogResponse, OperationLogResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/operations", response_model=list[OperationLogResponse])
def operations(db: Session = Depends(get_db), _user=Depends(require_permission("log:view"))) -> list[OperationLogResponse]:
    return [
        OperationLogResponse(
            id=item.id,
            user_id=item.user_id,
            action=item.action,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            detail=item.detail,
        )
        for item in db.scalars(select(OperationLog).order_by(OperationLog.id.desc()).limit(100))
    ]


@router.get("/models", response_model=list[ModelLogResponse])
def models(db: Session = Depends(get_db), _user=Depends(require_permission("log:view"))) -> list[ModelLogResponse]:
    return [
        ModelLogResponse(
            id=item.id,
            task_type=item.task_type,
            provider=item.provider,
            model=item.model,
            success=item.success,
            fallback_used=item.fallback_used,
            error_message=item.error_message,
        )
        for item in db.scalars(select(ModelLog).order_by(ModelLog.id.desc()).limit(100))
    ]
```

- [ ] **Step 2: Add admin role and user endpoints**

Create `backend/app/auth/admin_router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Permission, Role, User
from app.core.database import get_db
from app.core.deps import require_permission
from app.auth.service import permission_codes, role_codes, seed_rbac

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/roles")
def roles(db: Session = Depends(get_db), _user: User = Depends(require_permission("admin:role_manage"))):
    seed_rbac(db)
    return [
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "permissions": [permission.code for permission in role.permissions],
        }
        for role in db.scalars(select(Role)).all()
    ]


@router.post("/roles")
def create_role(payload: dict, db: Session = Depends(get_db), _user: User = Depends(require_permission("admin:role_manage"))):
    role = Role(
        code=payload["code"],
        name=payload["name"],
        description=payload.get("description", ""),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": role.id, "code": role.code, "name": role.name, "permissions": []}


@router.post("/roles/{role_id}/permissions")
def set_role_permissions(
    role_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("admin:role_manage")),
):
    role = db.get(Role, role_id)
    if role is None:
        return {"error": "role not found"}
    permissions = db.scalars(select(Permission).where(Permission.code.in_(payload["permission_codes"]))).all()
    role.permissions = list(permissions)
    db.commit()
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "permissions": [permission.code for permission in role.permissions],
    }


@router.get("/users")
def users(db: Session = Depends(get_db), _user: User = Depends(require_permission("admin:user_manage"))):
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "roles": role_codes(user),
            "permissions": permission_codes(user),
        }
        for user in db.scalars(select(User)).all()
    ]


@router.post("/users/{user_id}/roles")
def set_user_roles(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("admin:user_manage")),
):
    user = db.get(User, user_id)
    if user is None:
        return {"error": "user not found"}
    roles = db.scalars(select(Role).where(Role.code.in_(payload["role_codes"]))).all()
    user.roles = list(roles)
    db.commit()
    return {
        "id": user.id,
        "username": user.username,
        "roles": role_codes(user),
        "permissions": permission_codes(user),
    }
```

- [ ] **Step 3: Wire logs and admin routers**

Modify `backend/app/main.py`:

```python
from app.logs.router import router as logs_router
from app.auth.admin_router import router as admin_router

app.include_router(logs_router)
app.include_router(admin_router)
```

- [ ] **Step 4: Add README**

Create `README.md`:

```markdown
# 研备通 AI

面向成人考研机构的智能备课与教研辅助系统第一版。

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

健康检查：`http://127.0.0.1:8000/api/health`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`

## AI 配置

后端默认真实 API 优先，失败或未配置时 Mock 兜底。配置项在 `backend/.env`：

```env
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_API_KEY=
LLM_MODEL=mimo-v2.5-pro
LLM_MOCK_ON_FAILURE=true
```
```

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 6: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend frontend README.md
git commit -m "feat: add logs admin endpoints and docs"
```

## Self-Review

- Spec coverage: Tasks cover backend scaffold, RBAC, AI real-first Mock fallback, compliance, `txt/md/docx/pdf/pptx` parsing, lightweight retrieval, lesson generation/versioning, exercise generation/versioning, DOCX export, Vue teacher workbench pages, logs, and run instructions.
- First-version exclusions remain excluded: no vector database, no embedding, no OCR, no payment, no mobile app, no full market-analysis or ROI implementation.
- Type consistency: backend payloads use snake_case because FastAPI/Pydantic returns snake_case by default; frontend sends the same names.
- Permission consistency: teacher users receive `lesson:create`, `lesson:export`, `exercise:create`, and `material:upload` by default.
- Path consistency: backend endpoints match the approved spec except the plan uses `POST /api/lessons` and `POST /api/exercises` for initial save, which is clearer than putting creation under `{id}/save-version`.
