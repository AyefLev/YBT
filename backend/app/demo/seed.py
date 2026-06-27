from datetime import datetime, timezone
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.auth.service import seed_default_auth_data
from app.core.security import get_password_hash
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.exercises.models import Exercise, ExerciseVersion
from app.logs.models import JobLog, ModelLog, OperationLog
from app.materials.models import Material, MaterialChunk
from app.questions.models import QuestionBankItem
from app.questions.service import encode_list

DEMO_USERNAME = "demo_admin"
DEMO_PASSWORD = "Demo123456"
DEMO_EMAIL = "demo_admin@example.com"
DEMO_MANAGER_USERNAME = "demo_manager"
DEMO_MANAGER_PASSWORD = "Demo123456"
DEMO_MANAGER_EMAIL = "demo_manager@example.com"


def seed_demo_data(db: Session) -> dict[str, object]:
    seed_default_auth_data(db)
    admin_user = _upsert_demo_user(db)
    user = _upsert_demo_manager(db)
    course = _upsert_course(db, user)
    chapter = _upsert_chapter(db, course)
    session = _upsert_session(db, course, chapter)
    knowledge_point = _upsert_knowledge_point(db, course, chapter, session)
    material = _upsert_material(db, user)
    exercise = _upsert_exercise(db, user)
    question = _upsert_question(db, user, exercise, course, chapter, session, knowledge_point)
    _upsert_logs(db, user)
    db.flush()
    return {
        "username": DEMO_USERNAME,
        "password": DEMO_PASSWORD,
        "manager_username": DEMO_MANAGER_USERNAME,
        "manager_password": DEMO_MANAGER_PASSWORD,
        "admin_user_id": admin_user.id,
        "teaching_user_id": user.id,
        "course_id": course.id,
        "chapter_id": chapter.id,
        "session_id": session.id,
        "knowledge_point_id": knowledge_point.id,
        "material_id": material.id,
        "exercise_id": exercise.id,
        "question_id": question.id,
    }


def _upsert_demo_user(db: Session) -> User:
    admin_role = db.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        raise RuntimeError("Default admin role was not seeded.")

    user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    existing_email = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        if existing_email is not None:
            user = existing_email
            user.username = DEMO_USERNAME
        else:
            user = User(
                username=DEMO_USERNAME,
                email=DEMO_EMAIL,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                display_name="演示管理员",
                roles=[admin_role],
            )
            db.add(user)

    user.email = DEMO_EMAIL
    user.display_name = "演示管理员"
    user.hashed_password = get_password_hash(DEMO_PASSWORD)
    user.roles = [admin_role]
    user.is_active = True
    db.flush()
    return user


def _upsert_demo_manager(db: Session) -> User:
    manager_role = db.scalar(select(Role).where(Role.name == "teaching_manager"))
    if manager_role is None:
        raise RuntimeError("Default teaching_manager role was not seeded.")

    user = db.scalar(select(User).where(User.username == DEMO_MANAGER_USERNAME))
    existing_email = db.scalar(select(User).where(User.email == DEMO_MANAGER_EMAIL))
    if user is None:
        if existing_email is not None:
            user = existing_email
            user.username = DEMO_MANAGER_USERNAME
        else:
            user = User(
                username=DEMO_MANAGER_USERNAME,
                email=DEMO_MANAGER_EMAIL,
                hashed_password=get_password_hash(DEMO_MANAGER_PASSWORD),
                display_name="演示教管",
                roles=[manager_role],
            )
            db.add(user)

    user.email = DEMO_MANAGER_EMAIL
    user.display_name = "演示教管"
    user.hashed_password = get_password_hash(DEMO_MANAGER_PASSWORD)
    user.roles = [manager_role]
    user.is_active = True
    db.flush()
    return user


def _upsert_course(db: Session, user: User) -> Course:
    course = db.scalar(
        select(Course).where(
            Course.owner_id == user.id,
            Course.title == "考研数学线性代数强化班",
        )
    )
    if course is None:
        course = Course(
            owner_id=user.id,
            title="考研数学线性代数强化班",
            subject="数学",
            exam_type="成人考研",
        )
        db.add(course)

    course.subject = "数学"
    course.exam_type = "成人考研"
    course.description = "用于演示课程、知识库、习题生成、题库沉淀和观测日志的完整样例。"
    course.status = "active"
    db.flush()
    return course


def _upsert_chapter(db: Session, course: Course) -> Chapter:
    chapter = db.scalar(
        select(Chapter).where(
            Chapter.course_id == course.id,
            Chapter.title == "矩阵及其运算",
        )
    )
    if chapter is None:
        chapter = Chapter(course_id=course.id, title="矩阵及其运算")
        db.add(chapter)

    chapter.summary = "掌握矩阵乘法、单位矩阵和转置运算，为线性方程组和特征值学习打基础。"
    chapter.order_index = 1
    db.flush()
    return chapter


def _upsert_session(db: Session, course: Course, chapter: Chapter) -> LessonSession:
    session = db.scalar(
        select(LessonSession).where(
            LessonSession.course_id == course.id,
            LessonSession.chapter_id == chapter.id,
            LessonSession.title == "矩阵乘法与应用",
        )
    )
    if session is None:
        session = LessonSession(
            course_id=course.id,
            chapter_id=chapter.id,
            title="矩阵乘法与应用",
            duration_minutes=90,
        )
        db.add(session)

    session.duration_minutes = 90
    session.teaching_goal = "学生能够判断矩阵乘法是否存在，并完成基础矩阵乘法计算。"
    session.order_index = 1
    db.flush()
    return session


def _upsert_knowledge_point(
    db: Session,
    course: Course,
    chapter: Chapter,
    session: LessonSession,
) -> KnowledgePoint:
    point = db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.course_id == course.id,
            KnowledgePoint.name == "矩阵乘法",
        )
    )
    if point is None:
        point = KnowledgePoint(course_id=course.id, name="矩阵乘法")
        db.add(point)

    point.chapter_id = chapter.id
    point.session_id = session.id
    point.description = "矩阵乘法存在条件、结果阶数与行列乘积计算。"
    point.difficulty = "基础"
    db.flush()
    return point


def _upsert_material(db: Session, user: User) -> Material:
    material = db.scalar(
        select(Material).where(
            Material.uploader_id == user.id,
            Material.title == "矩阵乘法讲义片段",
        )
    )
    if material is None:
        material = Material(
            title="矩阵乘法讲义片段",
            file_name="matrix-demo.txt",
            file_type=".txt",
            file_path="demo://matrix-demo.txt",
            uploader_id=user.id,
        )
        db.add(material)
        db.flush()

    material.subject = "数学"
    material.purpose = "备课与习题生成"
    material.resource_scope = "public"
    material.tags_json = json.dumps(["矩阵", "线性代数", "演示数据"], ensure_ascii=False)
    material.parse_status = "parsed"
    material.parse_error = None
    db.query(MaterialChunk).filter(MaterialChunk.material_id == material.id).delete()
    material.chunks.clear()
    db.add(
        MaterialChunk(
            material_id=material.id,
            chunk_index=0,
            content=(
                "矩阵乘法 AB 存在的条件是 A 的列数等于 B 的行数。"
                "若 A 为 m×n 矩阵，B 为 n×p 矩阵，则 AB 为 m×p 矩阵。"
                "计算时，结果矩阵第 i 行第 j 列元素等于 A 的第 i 行与 B 的第 j 列对应元素乘积之和。"
            ),
            page_no=1,
            token_count=92,
        )
    )
    db.flush()
    return material


def _upsert_exercise(db: Session, user: User) -> Exercise:
    exercise = db.scalar(
        select(Exercise).where(
            Exercise.owner_id == user.id,
            Exercise.title == "矩阵乘法课堂练习",
        )
    )
    content = (
        "题目 1\n"
        "设矩阵 A 为 2×3，矩阵 B 为 3×2，判断 AB 的结果阶数。\n"
        "A. 2×2\n"
        "B. 3×3\n"
        "C. 2×3\n"
        "D. 不存在\n\n"
        "答案：A\n"
        "解析：A 的列数等于 B 的行数，乘积存在；结果阶数为 A 的行数乘 B 的列数，即 2×2。"
    )
    if exercise is None:
        exercise = Exercise(
            owner_id=user.id,
            title="矩阵乘法课堂练习",
            subject="数学",
            knowledge_point="矩阵乘法",
            question_type="选择题",
            difficulty="基础",
            current_content=content,
        )
        db.add(exercise)
        db.flush()

    exercise.subject = "数学"
    exercise.knowledge_point = "矩阵乘法"
    exercise.question_type = "选择题"
    exercise.difficulty = "基础"
    exercise.current_content = content
    exercise.compliance_level = "low"
    existing_version = db.scalar(
        select(ExerciseVersion).where(
            ExerciseVersion.exercise_id == exercise.id,
            ExerciseVersion.version_no == 1,
        )
    )
    if existing_version is None:
        db.add(
            ExerciseVersion(
                exercise_id=exercise.id,
                version_no=1,
                content=content,
                change_note="演示数据初始化",
            )
        )
    else:
        existing_version.content = content
        existing_version.change_note = "演示数据初始化"
    db.flush()
    return exercise


def _upsert_question(
    db: Session,
    user: User,
    exercise: Exercise,
    course: Course,
    chapter: Chapter,
    session: LessonSession,
    knowledge_point: KnowledgePoint,
) -> QuestionBankItem:
    question = db.scalar(
        select(QuestionBankItem).where(
            QuestionBankItem.owner_id == user.id,
            QuestionBankItem.source_exercise_id == exercise.id,
            QuestionBankItem.title == "矩阵乘法课堂练习 - 题目 1",
        )
    )
    if question is None:
        question = QuestionBankItem(
            owner_id=user.id,
            source_exercise_id=exercise.id,
            title="矩阵乘法课堂练习 - 题目 1",
            subject="数学",
            question_type="single_choice",
            difficulty="basic",
            stem="设矩阵 A 为 2×3，矩阵 B 为 3×2，判断 AB 的结果阶数。",
        )
        db.add(question)

    question.course_id = course.id
    question.chapter_id = chapter.id
    question.session_id = session.id
    question.knowledge_point_id = knowledge_point.id
    question.subject = "数学"
    question.question_type = "single_choice"
    question.difficulty = "basic"
    question.stem = "设矩阵 A 为 2×3，矩阵 B 为 3×2，判断 AB 的结果阶数。"
    question.options_json = encode_list(["A. 2×2", "B. 3×3", "C. 2×3", "D. 不存在"])
    question.answer = "A"
    question.analysis = "A 的列数等于 B 的行数，乘积存在；结果阶数为 A 的行数乘 B 的列数，即 2×2。"
    question.tags_json = encode_list(["矩阵乘法", "线性代数", "演示数据"])
    question.status = "draft"
    db.flush()
    return question


def _upsert_logs(db: Session, user: User) -> None:
    if db.scalar(select(ModelLog).where(ModelLog.task_type == "demo_seed")) is None:
        db.add(
            ModelLog(
                user_id=user.id,
                task_type="demo_seed",
                provider="demo",
                model="demo-seed",
                prompt_tokens=120,
                completion_tokens=80,
                latency_ms=320,
                success=True,
                fallback_used=False,
                status="success",
            )
        )
    if db.scalar(select(JobLog).where(JobLog.job_type == "demo_seed")) is None:
        now = datetime.now(timezone.utc)
        db.add(
            JobLog(
                job_type="demo_seed",
                status="succeeded",
                resource_type="demo",
                resource_id=user.id,
                user_id=user.id,
                detail="已初始化演示课程、材料、习题和题库题目",
                duration_ms=120,
                started_at=now,
                finished_at=now,
            )
        )
    if db.scalar(select(OperationLog).where(OperationLog.action == "demo:seed")) is None:
        db.add(
            OperationLog(
                user_id=user.id,
                action="demo:seed",
                resource="demo",
                detail="初始化演示账号、课程体系、知识库、习题、题库草稿和观测日志",
            )
        )
