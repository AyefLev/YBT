from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.classrooms.models import Assignment, AssignmentSubmission, Classroom
from app.classrooms.schemas import (
    AssignmentCreateRequest,
    AssignmentRead,
    AssignmentSubmissionRead,
    AssignmentSubmitRequest,
    ClassroomCreateRequest,
    ClassroomJoinRequest,
    ClassroomRead,
    ClassroomStudentRead,
    ClassroomUpdateRequest,
    SubmissionGradeRequest,
)
from app.classrooms.service import (
    archive_classroom,
    create_assignment,
    create_classroom,
    get_accessible_classroom,
    get_assignment,
    get_submission,
    grade_submission,
    join_classroom,
    list_accessible_classrooms,
    list_assignment_submissions,
    list_assignments,
    list_classroom_students,
    list_my_assignments,
    submit_assignment,
    update_classroom,
)
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission

router = APIRouter(prefix="/api", tags=["classrooms"])


def classroom_to_read(classroom: Classroom, db: Session) -> ClassroomRead:
    teacher = db.get(User, classroom.teacher_id)
    return ClassroomRead(
        id=classroom.id,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.display_name if teacher else "",
        teacher_username=teacher.username if teacher else "",
        course_id=classroom.course_id,
        name=classroom.name,
        description=classroom.description,
        invite_code=classroom.invite_code,
        status=classroom.status,
        student_count=len([item for item in classroom.enrollments if item.status == "active"]),
        assignment_count=len(classroom.assignments),
        created_at=classroom.created_at,
        updated_at=classroom.updated_at,
    )


def assignment_to_read(
    assignment: Assignment,
    *,
    submission: AssignmentSubmission | None = None,
) -> AssignmentRead:
    return AssignmentRead(
        id=assignment.id,
        classroom_id=assignment.classroom_id,
        title=assignment.title,
        description=assignment.description,
        instructions=assignment.instructions,
        exercise_id=assignment.exercise_id,
        material_id=assignment.material_id,
        due_at=assignment.due_at,
        status=assignment.status,
        submission_status=submission.status if submission else None,
        score=submission.score if submission else None,
        feedback=submission.feedback if submission else "",
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


def submission_to_read(
    submission: AssignmentSubmission,
    *,
    student_name: str = "",
) -> AssignmentSubmissionRead:
    return AssignmentSubmissionRead(
        id=submission.id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        student_name=student_name,
        content=submission.content,
        status=submission.status,
        score=submission.score,
        feedback=submission.feedback,
        submitted_at=submission.submitted_at,
        graded_at=submission.graded_at,
    )


def _classroom_or_404(db: Session, classroom_id: int, current_user: User) -> Classroom:
    classroom = get_accessible_classroom(db, classroom_id=classroom_id, current_user=current_user)
    if classroom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    return classroom


def _manageable_classroom_or_404(db: Session, classroom_id: int, current_user: User) -> Classroom:
    classroom = _classroom_or_404(db, classroom_id, current_user)
    if "class:manage_all" in current_user.permission_codes:
        return classroom
    if "class:manage" in current_user.permission_codes and classroom.teacher_id == current_user.id:
        return classroom
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _can_read_classroom_management_data(current_user: User, classroom: Classroom) -> bool:
    return (
        "class:view_all" in current_user.permission_codes
        or "class:manage_all" in current_user.permission_codes
        or (
            "class:manage" in current_user.permission_codes
            and classroom.teacher_id == current_user.id
        )
    )


def _can_read_assignment_submissions(current_user: User, classroom: Classroom) -> bool:
    return (
        "assignment:view_all" in current_user.permission_codes
        or "class:manage_all" in current_user.permission_codes
        or (
            "assignment:grade" in current_user.permission_codes
            and classroom.teacher_id == current_user.id
        )
    )


def _assignment_or_404(db: Session, assignment_id: int, current_user: User) -> Assignment:
    assignment = get_assignment(db, assignment_id=assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    _classroom_or_404(db, assignment.classroom_id, current_user)
    return assignment


@router.post("/classrooms", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED)
def create_current_user_classroom(
    payload: ClassroomCreateRequest,
    current_user: User = Depends(require_permission("class:manage")),
    db: Session = Depends(get_db),
) -> ClassroomRead:
    classroom = create_classroom(db, payload=payload, current_user=current_user)
    response = classroom_to_read(classroom, db)
    db.commit()
    return response


@router.get("/classrooms", response_model=list[ClassroomRead])
def list_classrooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClassroomRead]:
    return [
        classroom_to_read(classroom, db)
        for classroom in list_accessible_classrooms(db, current_user=current_user)
    ]


@router.post("/classrooms/join", response_model=ClassroomRead)
def join_classroom_by_code(
    payload: ClassroomJoinRequest,
    current_user: User = Depends(require_permission("class:join")),
    db: Session = Depends(get_db),
) -> ClassroomRead:
    classroom = join_classroom(db, invite_code=payload.invite_code, current_user=current_user)
    db.commit()
    db.refresh(classroom)
    return classroom_to_read(classroom, db)


@router.get("/classrooms/{classroom_id}", response_model=ClassroomRead)
def get_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassroomRead:
    return classroom_to_read(_classroom_or_404(db, classroom_id, current_user), db)


@router.patch("/classrooms/{classroom_id}", response_model=ClassroomRead)
def update_current_user_classroom(
    classroom_id: int,
    payload: ClassroomUpdateRequest,
    current_user: User = Depends(require_permission("class:manage")),
    db: Session = Depends(get_db),
) -> ClassroomRead:
    classroom = _manageable_classroom_or_404(db, classroom_id, current_user)
    updated = update_classroom(db, classroom=classroom, payload=payload, current_user=current_user)
    response = classroom_to_read(updated, db)
    db.commit()
    return response


@router.delete("/classrooms/{classroom_id}", response_model=ClassroomRead)
def delete_current_user_classroom(
    classroom_id: int,
    current_user: User = Depends(require_permission("class:manage")),
    db: Session = Depends(get_db),
) -> ClassroomRead:
    classroom = _manageable_classroom_or_404(db, classroom_id, current_user)
    archived = archive_classroom(db, classroom=classroom)
    response = classroom_to_read(archived, db)
    db.commit()
    return response


@router.get("/classrooms/{classroom_id}/students", response_model=list[ClassroomStudentRead])
def get_classroom_students(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClassroomStudentRead]:
    classroom = _classroom_or_404(db, classroom_id, current_user)
    if not _can_read_classroom_management_data(current_user, classroom):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return [
        ClassroomStudentRead(
            id=student.id,
            username=student.username,
            email=student.email,
            display_name=student.display_name,
            enrollment_status=enrollment.status,
            joined_at=enrollment.joined_at,
        )
        for student, enrollment in list_classroom_students(db, classroom=classroom)
    ]


@router.post(
    "/classrooms/{classroom_id}/assignments",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_classroom_assignment(
    classroom_id: int,
    payload: AssignmentCreateRequest,
    current_user: User = Depends(require_permission("assignment:manage")),
    db: Session = Depends(get_db),
) -> AssignmentRead:
    classroom = _manageable_classroom_or_404(db, classroom_id, current_user)
    assignment = create_assignment(db, classroom=classroom, payload=payload)
    response = assignment_to_read(assignment)
    db.commit()
    return response


@router.get("/classrooms/{classroom_id}/assignments", response_model=list[AssignmentRead])
def get_classroom_assignments(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    classroom = _classroom_or_404(db, classroom_id, current_user)
    return [
        assignment_to_read(assignment)
        for assignment in list_assignments(db, classroom=classroom, current_user=current_user)
    ]


@router.get("/assignments/my", response_model=list[AssignmentRead])
def get_my_assignments(
    current_user: User = Depends(require_permission("assignment:submit")),
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    assignments = list_my_assignments(db, current_user=current_user)
    submissions = {
        submission.assignment_id: submission
        for submission in db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.assignment_id.in_([item.id for item in assignments] or [0]),
        )
        .all()
    }
    return [
        assignment_to_read(assignment, submission=submissions.get(assignment.id))
        for assignment in assignments
    ]


@router.post("/assignments/{assignment_id}/submit", response_model=AssignmentSubmissionRead)
def submit_current_user_assignment(
    assignment_id: int,
    payload: AssignmentSubmitRequest,
    current_user: User = Depends(require_permission("assignment:submit")),
    db: Session = Depends(get_db),
) -> AssignmentSubmissionRead:
    assignment = _assignment_or_404(db, assignment_id, current_user)
    submission = submit_assignment(db, assignment=assignment, payload=payload, current_user=current_user)
    response = submission_to_read(submission, student_name=current_user.display_name)
    db.commit()
    return response


@router.get("/assignments/{assignment_id}/submissions", response_model=list[AssignmentSubmissionRead])
def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssignmentSubmissionRead]:
    assignment = _assignment_or_404(db, assignment_id, current_user)
    classroom = _classroom_or_404(db, assignment.classroom_id, current_user)
    if not _can_read_assignment_submissions(current_user, classroom):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    submissions = list_assignment_submissions(db, assignment=assignment)
    students_by_id = {
        student.id: student
        for student in db.query(User)
        .filter(User.id.in_([item.student_id for item in submissions] or [0]))
        .all()
    }
    return [
        submission_to_read(
            submission,
            student_name=students_by_id.get(submission.student_id).display_name
            if submission.student_id in students_by_id
            else "",
        )
        for submission in submissions
    ]


@router.post("/submissions/{submission_id}/grade", response_model=AssignmentSubmissionRead)
def grade_assignment_submission(
    submission_id: int,
    payload: SubmissionGradeRequest,
    current_user: User = Depends(require_permission("assignment:grade")),
    db: Session = Depends(get_db),
) -> AssignmentSubmissionRead:
    submission = get_submission(db, submission_id=submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    assignment = _assignment_or_404(db, submission.assignment_id, current_user)
    _manageable_classroom_or_404(db, assignment.classroom_id, current_user)
    graded = grade_submission(db, submission=submission, payload=payload)
    student = db.get(User, graded.student_id)
    response = submission_to_read(graded, student_name=student.display_name if student else "")
    db.commit()
    return response
