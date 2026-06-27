from datetime import datetime, timezone
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.classrooms.models import (
    Assignment,
    AssignmentSubmission,
    Classroom,
    ClassroomEnrollment,
)
from app.classrooms.schemas import (
    AssignmentCreateRequest,
    AssignmentSubmitRequest,
    ClassroomCreateRequest,
    ClassroomUpdateRequest,
    SubmissionGradeRequest,
)
from app.courses.models import Course


def create_classroom(
    db: Session,
    *,
    payload: ClassroomCreateRequest,
    current_user: User,
) -> Classroom:
    _ensure_teacher_can_use_course(db, payload.course_id, current_user)
    classroom = Classroom(
        teacher_id=current_user.id,
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        invite_code=_generate_invite_code(db),
    )
    db.add(classroom)
    db.flush()
    return classroom


def list_accessible_classrooms(db: Session, *, current_user: User) -> list[Classroom]:
    statement = select(Classroom).options(
        selectinload(Classroom.enrollments),
        selectinload(Classroom.assignments),
    )
    if _can_view_all_classrooms(current_user):
        pass
    elif _has(current_user, "class:manage"):
        statement = statement.where(Classroom.teacher_id == current_user.id)
    else:
        statement = statement.join(ClassroomEnrollment).where(
            ClassroomEnrollment.student_id == current_user.id,
            ClassroomEnrollment.status == "active",
            Classroom.status == "active",
        )
    return list(
        db.scalars(statement.order_by(Classroom.created_at.desc(), Classroom.id.desc())).all()
    )


def get_accessible_classroom(
    db: Session,
    *,
    classroom_id: int,
    current_user: User,
) -> Classroom | None:
    classroom = db.scalar(
        select(Classroom)
        .options(selectinload(Classroom.enrollments), selectinload(Classroom.assignments))
        .where(Classroom.id == classroom_id)
    )
    if classroom is None:
        return None
    if _can_manage_classroom(current_user, classroom) or _can_view_all_classrooms(current_user):
        return classroom
    if _is_enrolled(db, classroom_id=classroom.id, student_id=current_user.id):
        return classroom
    return None


def update_classroom(
    db: Session,
    *,
    classroom: Classroom,
    payload: ClassroomUpdateRequest,
    current_user: User,
) -> Classroom:
    _ensure_teacher_can_use_course(db, payload.course_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(classroom, field_name, value)
    db.flush()
    return classroom


def archive_classroom(db: Session, *, classroom: Classroom) -> Classroom:
    classroom.status = "archived"
    db.flush()
    return classroom


def join_classroom(db: Session, *, invite_code: str, current_user: User) -> Classroom:
    if not _has(current_user, "class:join"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can join classes")

    classroom = db.scalar(
        select(Classroom).where(
            Classroom.invite_code == invite_code.strip().upper(),
            Classroom.status == "active",
        )
    )
    if classroom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    enrollment = db.scalar(
        select(ClassroomEnrollment).where(
            ClassroomEnrollment.classroom_id == classroom.id,
            ClassroomEnrollment.student_id == current_user.id,
        )
    )
    if enrollment is None:
        db.add(ClassroomEnrollment(classroom_id=classroom.id, student_id=current_user.id))
    else:
        enrollment.status = "active"
    db.flush()
    return classroom


def list_classroom_students(db: Session, *, classroom: Classroom) -> list[tuple[User, ClassroomEnrollment]]:
    enrollments = list(
        db.scalars(
            select(ClassroomEnrollment)
            .where(ClassroomEnrollment.classroom_id == classroom.id)
            .order_by(ClassroomEnrollment.joined_at, ClassroomEnrollment.id)
        ).all()
    )
    students_by_id = {
        student.id: student
        for student in db.scalars(
            select(User).where(User.id.in_([item.student_id for item in enrollments] or [0]))
        ).all()
    }
    return [
        (students_by_id[enrollment.student_id], enrollment)
        for enrollment in enrollments
        if enrollment.student_id in students_by_id
    ]


def create_assignment(
    db: Session,
    *,
    classroom: Classroom,
    payload: AssignmentCreateRequest,
) -> Assignment:
    assignment = Assignment(
        classroom_id=classroom.id,
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        exercise_id=payload.exercise_id,
        material_id=payload.material_id,
        due_at=payload.due_at,
        status=payload.status,
    )
    db.add(assignment)
    db.flush()
    return assignment


def list_assignments(
    db: Session,
    *,
    classroom: Classroom,
    current_user: User,
) -> list[Assignment]:
    statement = select(Assignment).where(Assignment.classroom_id == classroom.id)
    if not _can_manage_classroom(current_user, classroom) and not _has(current_user, "assignment:view_all"):
        statement = statement.where(Assignment.status == "published")
    return list(db.scalars(statement.order_by(Assignment.created_at.desc(), Assignment.id.desc())).all())


def list_my_assignments(db: Session, *, current_user: User) -> list[Assignment]:
    classroom_ids = [
        enrollment.classroom_id
        for enrollment in db.scalars(
            select(ClassroomEnrollment).where(
                ClassroomEnrollment.student_id == current_user.id,
                ClassroomEnrollment.status == "active",
            )
        ).all()
    ]
    if not classroom_ids:
        return []
    return list(
        db.scalars(
            select(Assignment)
            .where(
                Assignment.classroom_id.in_(classroom_ids),
                Assignment.status == "published",
            )
            .order_by(Assignment.created_at.desc(), Assignment.id.desc())
        ).all()
    )


def submit_assignment(
    db: Session,
    *,
    assignment: Assignment,
    payload: AssignmentSubmitRequest,
    current_user: User,
) -> AssignmentSubmission:
    if not _is_enrolled(db, classroom_id=assignment.classroom_id, student_id=current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    if submission is None:
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=current_user.id,
        )
        db.add(submission)
    submission.content = payload.content
    submission.status = "submitted"
    submission.submitted_at = datetime.now(timezone.utc)
    db.flush()
    return submission


def list_assignment_submissions(
    db: Session,
    *,
    assignment: Assignment,
) -> list[AssignmentSubmission]:
    return list(
        db.scalars(
            select(AssignmentSubmission)
            .where(AssignmentSubmission.assignment_id == assignment.id)
            .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        ).all()
    )


def grade_submission(
    db: Session,
    *,
    submission: AssignmentSubmission,
    payload: SubmissionGradeRequest,
) -> AssignmentSubmission:
    submission.score = payload.score
    submission.feedback = payload.feedback
    submission.status = "graded"
    submission.graded_at = datetime.now(timezone.utc)
    db.flush()
    return submission


def get_assignment(db: Session, *, assignment_id: int) -> Assignment | None:
    return db.get(Assignment, assignment_id)


def get_submission(db: Session, *, submission_id: int) -> AssignmentSubmission | None:
    return db.get(AssignmentSubmission, submission_id)


def _ensure_teacher_can_use_course(
    db: Session,
    course_id: int | None,
    current_user: User,
) -> None:
    if course_id is None:
        return
    statement = select(Course).where(Course.id == course_id)
    if not _has(current_user, "course:manage_all"):
        statement = statement.where(Course.owner_id == current_user.id)
    if db.scalar(statement) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")


def _generate_invite_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if db.scalar(select(Classroom).where(Classroom.invite_code == code)) is None:
            return code
    raise RuntimeError("Could not generate unique classroom invite code.")


def _is_enrolled(db: Session, *, classroom_id: int, student_id: int) -> bool:
    return (
        db.scalar(
            select(ClassroomEnrollment).where(
                ClassroomEnrollment.classroom_id == classroom_id,
                ClassroomEnrollment.student_id == student_id,
                ClassroomEnrollment.status == "active",
            )
        )
        is not None
    )


def _has(user: User, permission: str) -> bool:
    return permission in user.permission_codes


def _can_manage_classroom(user: User, classroom: Classroom) -> bool:
    return _has(user, "class:manage_all") or (
        _has(user, "class:manage") and classroom.teacher_id == user.id
    )


def _can_view_all_classrooms(user: User) -> bool:
    return _has(user, "class:view_all") or _has(user, "class:manage_all")
