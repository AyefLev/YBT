from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.database import get_session_local, init_db


def create_app(settings: Settings | None = None) -> FastAPI:
    from app.ai.router import router as ai_router
    from app.ai import models as ai_models  # noqa: F401
    from app.auth.admin_router import router as admin_router
    from app.auth.router import router as auth_router
    from app.auth.service import seed_bootstrap_admin, seed_default_auth_data
    from app.classrooms import models as classroom_models  # noqa: F401
    from app.classrooms.router import router as classrooms_router
    from app.compliance import models as compliance_models  # noqa: F401
    from app.compliance.router import router as compliance_router
    from app.courses import models as courses_models  # noqa: F401
    from app.courses.router import router as courses_router
    from app.exercises import models as exercises_models  # noqa: F401
    from app.exercises.router import router as exercises_router
    from app.exports import models as exports_models  # noqa: F401
    from app.exports.router import router as exports_router
    from app.lessons import models as lessons_models  # noqa: F401
    from app.lessons.router import router as lessons_router
    from app.logs import models as logs_models  # noqa: F401
    from app.logs.router import router as logs_router
    from app.materials import models as materials_models  # noqa: F401
    from app.materials.router import router as materials_router
    from app.questions import models as questions_models  # noqa: F401
    from app.presentations.router import router as presentations_router
    from app.questions.router import router as questions_router
    from app.retrieval.router import router as retrieval_router
    from app.reviews.router import router as reviews_router

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active_settings = settings or get_settings()
        active_settings.validate_jwt_secret()
        init_db(active_settings.database_url)
        session_local = get_session_local(active_settings.database_url)
        with session_local() as db:
            seed_default_auth_data(db)
            seed_bootstrap_admin(db, active_settings)
        yield

    app = FastAPI(title="研备通 AI", version="0.1.0", lifespan=lifespan)

    app.include_router(ai_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(classrooms_router)
    app.include_router(compliance_router)
    app.include_router(materials_router)
    app.include_router(retrieval_router)
    app.include_router(courses_router)
    app.include_router(questions_router)
    app.include_router(lessons_router)
    app.include_router(exercises_router)
    app.include_router(presentations_router)
    app.include_router(reviews_router)
    app.include_router(exports_router)
    app.include_router(logs_router)

    @app.get("/")
    def root() -> dict[str, str]:
        active_settings = settings or get_settings()
        return {
            "app": active_settings.app_name,
            "health": "/api/health",
            "docs": "/docs",
            "gateway": "http://localhost:8080",
            "frontend": "http://localhost:8080",
        }

    @app.get("/api/health")
    def health() -> dict[str, str]:
        active_settings = settings or get_settings()
        return {"status": "ok", "app": active_settings.app_name}

    return app


app = create_app()
