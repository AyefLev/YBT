from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine(database_url: str | None = None) -> Engine:
    return _get_engine(database_url or get_settings().database_url)


@lru_cache
def _get_engine(database_url: str) -> Engine:
    connect_args = _connect_args(database_url)
    if connect_args:
        return create_engine(database_url, connect_args=connect_args)
    return create_engine(database_url)


def get_session_local(database_url: str | None = None) -> sessionmaker[Session]:
    return _get_session_local(database_url or get_settings().database_url)


@lru_cache
def _get_session_local(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        autocommit=False,
    )


def clear_database_caches() -> None:
    _get_engine.cache_clear()
    _get_session_local.cache_clear()


def init_db(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    _apply_common_compatibility_migrations(engine)
    _apply_sqlite_compatibility_migrations(engine)


def _apply_common_compatibility_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    _apply_users_account_migration(engine, inspector)
    _apply_material_resource_scope_migration(engine, inspector)
    _apply_material_teaching_scope_migration(engine, inspector)
    _apply_material_chunking_migration(engine, inspector)
    _apply_lesson_teaching_scope_migration(engine, inspector)
    _apply_exercise_teaching_scope_migration(engine, inspector)
    _apply_model_log_token_migration(engine, inspector)
    _apply_ai_provider_pricing_migration(engine, inspector)


def _apply_users_account_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    reviewed_at_type = (
        "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME"
    )
    is_active_default = "true" if engine.dialect.name == "postgresql" else "1"
    migrations = {
        "is_active": f"ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT {is_active_default}",
        "requested_role": "ALTER TABLE users ADD COLUMN requested_role VARCHAR(32) NOT NULL DEFAULT 'teacher'",
        "account_status": "ALTER TABLE users ADD COLUMN account_status VARCHAR(32) NOT NULL DEFAULT 'approved'",
        "review_note": "ALTER TABLE users ADD COLUMN review_note TEXT NOT NULL DEFAULT ''",
        "reviewed_by_id": "ALTER TABLE users ADD COLUMN reviewed_by_id INTEGER",
        "reviewed_at": f"ALTER TABLE users ADD COLUMN reviewed_at {reviewed_at_type}",
    }

    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))


def _apply_material_resource_scope_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("materials"):
        return

    columns = {column["name"] for column in inspector.get_columns("materials")}
    if "resource_scope" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE materials ADD COLUMN resource_scope "
                "VARCHAR(32) NOT NULL DEFAULT 'personal'"
            )
        )


def _apply_material_teaching_scope_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="materials",
        migrations={
            "course_id": "ALTER TABLE materials ADD COLUMN course_id INTEGER",
            "chapter_id": "ALTER TABLE materials ADD COLUMN chapter_id INTEGER",
            "session_id": "ALTER TABLE materials ADD COLUMN session_id INTEGER",
            "knowledge_point_id": "ALTER TABLE materials ADD COLUMN knowledge_point_id INTEGER",
        },
    )


def _apply_material_chunking_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="materials",
        migrations={
            "chunk_strategy": "ALTER TABLE materials ADD COLUMN chunk_strategy VARCHAR(32) NOT NULL DEFAULT 'fixed'",
            "chunk_size": "ALTER TABLE materials ADD COLUMN chunk_size INTEGER NOT NULL DEFAULT 800",
            "chunk_overlap": "ALTER TABLE materials ADD COLUMN chunk_overlap INTEGER NOT NULL DEFAULT 80",
        },
    )


def _apply_lesson_teaching_scope_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="lessons",
        migrations={
            "course_id": "ALTER TABLE lessons ADD COLUMN course_id INTEGER",
            "chapter_id": "ALTER TABLE lessons ADD COLUMN chapter_id INTEGER",
            "session_id": "ALTER TABLE lessons ADD COLUMN session_id INTEGER",
            "knowledge_point_id": "ALTER TABLE lessons ADD COLUMN knowledge_point_id INTEGER",
            "material_ids_json": "ALTER TABLE lessons ADD COLUMN material_ids_json TEXT NOT NULL DEFAULT '[]'",
            "prompt_template": "ALTER TABLE lessons ADD COLUMN prompt_template TEXT NOT NULL DEFAULT ''",
            "output_format": "ALTER TABLE lessons ADD COLUMN output_format TEXT NOT NULL DEFAULT ''",
        },
    )


def _apply_exercise_teaching_scope_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="exercises",
        migrations={
            "course_id": "ALTER TABLE exercises ADD COLUMN course_id INTEGER",
            "chapter_id": "ALTER TABLE exercises ADD COLUMN chapter_id INTEGER",
            "session_id": "ALTER TABLE exercises ADD COLUMN session_id INTEGER",
            "knowledge_point_id": "ALTER TABLE exercises ADD COLUMN knowledge_point_id INTEGER",
            "lesson_id": "ALTER TABLE exercises ADD COLUMN lesson_id INTEGER",
            "material_ids_json": "ALTER TABLE exercises ADD COLUMN material_ids_json TEXT NOT NULL DEFAULT '[]'",
            "prompt_template": "ALTER TABLE exercises ADD COLUMN prompt_template TEXT NOT NULL DEFAULT ''",
            "output_format": "ALTER TABLE exercises ADD COLUMN output_format TEXT NOT NULL DEFAULT ''",
        },
    )


def _apply_model_log_token_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="model_logs",
        migrations={
            "user_id": "ALTER TABLE model_logs ADD COLUMN user_id INTEGER",
            "prompt_tokens": "ALTER TABLE model_logs ADD COLUMN prompt_tokens INTEGER",
            "completion_tokens": "ALTER TABLE model_logs ADD COLUMN completion_tokens INTEGER",
            "api_role": "ALTER TABLE model_logs ADD COLUMN api_role VARCHAR(32) NOT NULL DEFAULT ''",
            "api_base_url": "ALTER TABLE model_logs ADD COLUMN api_base_url VARCHAR(1024) NOT NULL DEFAULT ''",
            "estimated_cost": "ALTER TABLE model_logs ADD COLUMN estimated_cost FLOAT NOT NULL DEFAULT 0",
            "cost_currency": "ALTER TABLE model_logs ADD COLUMN cost_currency VARCHAR(16) NOT NULL DEFAULT 'CNY'",
        },
    )


def _apply_ai_provider_pricing_migration(engine: Engine, inspector) -> None:
    _apply_columns_if_missing(
        engine,
        inspector,
        table_name="ai_provider_configs",
        migrations={
            "prompt_price_per_1k": "ALTER TABLE ai_provider_configs ADD COLUMN prompt_price_per_1k FLOAT NOT NULL DEFAULT 0",
            "completion_price_per_1k": "ALTER TABLE ai_provider_configs ADD COLUMN completion_price_per_1k FLOAT NOT NULL DEFAULT 0",
            "currency": "ALTER TABLE ai_provider_configs ADD COLUMN currency VARCHAR(16) NOT NULL DEFAULT 'CNY'",
        },
    )


def _apply_columns_if_missing(
    engine: Engine,
    inspector,
    *,
    table_name: str,
    migrations: dict[str, str],
) -> None:
    if not inspector.has_table(table_name):
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))


def _apply_sqlite_compatibility_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    _apply_sqlite_users_migration(engine, inspector)
    _apply_sqlite_model_logs_migration(engine, inspector)
    _apply_sqlite_materials_migration(engine, inspector)
    _apply_sqlite_lesson_versions_migration(engine, inspector)
    _apply_sqlite_exercise_versions_migration(engine, inspector)
    _apply_sqlite_course_hierarchy_migration(engine, inspector)
    _apply_sqlite_lessons_review_migration(engine, inspector)


def _apply_sqlite_users_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_active" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
        )


def _apply_sqlite_model_logs_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("model_logs"):
        return

    columns = {column["name"] for column in inspector.get_columns("model_logs")}
    migrations = {
        "task_type": "ALTER TABLE model_logs ADD COLUMN task_type VARCHAR(64) NOT NULL DEFAULT 'unknown'",
        "latency_ms": "ALTER TABLE model_logs ADD COLUMN latency_ms INTEGER NOT NULL DEFAULT 0",
        "success": "ALTER TABLE model_logs ADD COLUMN success BOOLEAN NOT NULL DEFAULT 1",
        "fallback_used": "ALTER TABLE model_logs ADD COLUMN fallback_used BOOLEAN NOT NULL DEFAULT 0",
        "error_message": "ALTER TABLE model_logs ADD COLUMN error_message TEXT NOT NULL DEFAULT ''",
    }

    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))


def _apply_sqlite_materials_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("materials"):
        return

    columns = {column["name"] for column in inspector.get_columns("materials")}
    migrations = {
        "subject": "ALTER TABLE materials ADD COLUMN subject VARCHAR(128) NOT NULL DEFAULT ''",
        "purpose": "ALTER TABLE materials ADD COLUMN purpose VARCHAR(128) NOT NULL DEFAULT ''",
        "tags": "ALTER TABLE materials ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
        "parse_error": "ALTER TABLE materials ADD COLUMN parse_error TEXT",
    }

    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))


def _apply_sqlite_lesson_versions_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("lesson_versions"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("lesson_versions")}
    if "uq_lesson_version_no" in indexes:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_lesson_version_no "
                "ON lesson_versions (lesson_id, version_no)"
            )
        )


def _apply_sqlite_exercise_versions_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("exercise_versions"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("exercise_versions")}
    if "uq_exercise_version_no" in indexes:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_exercise_version_no "
                "ON exercise_versions (exercise_id, version_no)"
            )
        )


def _apply_sqlite_course_hierarchy_migration(engine: Engine, inspector) -> None:
    has_course_chapters = inspector.has_table("course_chapters")
    has_chapters = inspector.has_table("chapters")

    if has_course_chapters:
        with engine.begin() as connection:
            if has_chapters:
                current_count = connection.execute(
                    text("SELECT COUNT(*) FROM chapters")
                ).scalar_one()
                if current_count == 0:
                    connection.execute(text("DROP TABLE chapters"))
                    connection.execute(
                        text("ALTER TABLE course_chapters RENAME TO chapters")
                    )
            else:
                connection.execute(
                    text("ALTER TABLE course_chapters RENAME TO chapters")
                )

    inspector = inspect(engine)
    if not inspector.has_table("lesson_sessions"):
        return

    columns = {column["name"] for column in inspector.get_columns("lesson_sessions")}
    if "course_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE lesson_sessions ADD COLUMN course_id INTEGER"))
        if inspector.has_table("chapters"):
            connection.execute(
                text(
                    "UPDATE lesson_sessions "
                    "SET course_id = ("
                    "SELECT chapters.course_id FROM chapters "
                    "WHERE chapters.id = lesson_sessions.chapter_id"
                    ") "
                    "WHERE course_id IS NULL"
                )
            )


def _apply_sqlite_lessons_review_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("lessons"):
        return

    columns = {column["name"] for column in inspector.get_columns("lessons")}
    migrations = {
        "review_status": "ALTER TABLE lessons ADD COLUMN review_status VARCHAR(32) NOT NULL DEFAULT 'draft'",
        "reviewer_id": "ALTER TABLE lessons ADD COLUMN reviewer_id INTEGER",
        "review_comment": "ALTER TABLE lessons ADD COLUMN review_comment TEXT NOT NULL DEFAULT ''",
        "reviewed_at": "ALTER TABLE lessons ADD COLUMN reviewed_at DATETIME",
    }

    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
