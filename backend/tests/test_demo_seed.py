def test_seed_demo_data_creates_idempotent_demo_assets(client):
    from sqlalchemy import select

    from app.auth.models import User
    from app.core.database import get_session_local
    from app.courses.models import Course
    from app.demo.seed import DEMO_MANAGER_USERNAME, DEMO_USERNAME, seed_demo_data
    from app.exercises.models import Exercise
    from app.logs.models import JobLog, ModelLog, OperationLog
    from app.materials.models import Material
    from app.questions.models import QuestionBankItem

    session_local = get_session_local()
    with session_local() as db:
        first = seed_demo_data(db)
        db.commit()
        second = seed_demo_data(db)
        db.commit()

        admin_user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
        manager_user = db.scalar(select(User).where(User.username == DEMO_MANAGER_USERNAME))
        courses = db.scalars(select(Course).where(Course.owner_id == manager_user.id)).all()
        materials = db.scalars(select(Material).where(Material.uploader_id == manager_user.id)).all()
        exercises = db.scalars(select(Exercise).where(Exercise.owner_id == manager_user.id)).all()
        questions = db.scalars(select(QuestionBankItem).where(QuestionBankItem.owner_id == manager_user.id)).all()
        model_logs = db.scalars(select(ModelLog).where(ModelLog.task_type == "demo_seed")).all()
        job_logs = db.scalars(select(JobLog).where(JobLog.job_type == "demo_seed")).all()
        operation_logs = db.scalars(select(OperationLog).where(OperationLog.action == "demo:seed")).all()
        admin_role_names = sorted(admin_user.role_names)
        manager_role_names = sorted(manager_user.role_names)
        chapter_count = len(courses[0].chapters)
        session_count = len(courses[0].chapters[0].sessions)
        knowledge_point_count = len(courses[0].knowledge_points)
        material_chunk_count = len(materials[0].chunks)
        material_title = materials[0].title
        exercise_content = exercises[0].current_content

    assert first["username"] == DEMO_USERNAME
    assert second["username"] == DEMO_USERNAME
    assert first["manager_username"] == DEMO_MANAGER_USERNAME
    assert admin_user is not None
    assert manager_user is not None
    assert admin_role_names == ["admin"]
    assert manager_role_names == ["teaching_manager"]
    assert len(courses) == 1
    assert chapter_count == 1
    assert session_count == 1
    assert knowledge_point_count == 1
    assert len(materials) == 1
    assert material_chunk_count >= 1
    assert material_title == "矩阵乘法讲义片段"
    assert len(exercises) == 1
    assert "矩阵 A" in exercise_content
    assert len(questions) == 1
    assert questions[0].source_exercise_id == exercises[0].id
    assert len(model_logs) == 1
    assert len(job_logs) == 1
    assert len(operation_logs) == 1
