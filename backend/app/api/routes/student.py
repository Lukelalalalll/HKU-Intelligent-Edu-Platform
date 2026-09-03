from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models import Assignment, Course, Enrollment, Submission, User, UserRole
from app.schemas import (
    CourseOut,
    ScheduleIn,
    StudentAssignmentReminderOut,
    StudentDashboardOut,
    StudentScheduleOut,
)

router = APIRouter(prefix="/api/student", tags=["student"])


def _serialize_course(course: Course) -> CourseOut:
    return CourseOut(
        id=course.id,
        code=course.code,
        name=course.name,
        description=course.description,
        teacher_id=course.teacher_id,
        academic_year_start=course.academic_year_start,
        semester=course.semester,
        timezone=course.timezone,
        teacher_name=course.teacher.name,
        enrolled_count=len(course.enrollments),
        schedules=[ScheduleIn.model_validate(schedule, from_attributes=True) for schedule in course.schedules],
    )


def _submission_status(assignment: Assignment, submission, now: datetime) -> tuple[str, datetime | None, int | None]:
    if submission is None:
        due_at = assignment.due_at
        if due_at is not None:
            comparable_due = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
            if comparable_due < now:
                return "overdue", None, None
        return "not_started", None, None
    if submission.score is not None:
        return "graded", submission.submitted_at, submission.score
    return "submitted", submission.submitted_at, None


@router.get("/dashboard", response_model=StudentDashboardOut)
def student_dashboard(
    user: User = Depends(require_roles(UserRole.student)),
    db: Session = Depends(get_db),
):
    courses = db.scalars(
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == user.id)
        .options(
            selectinload(Course.teacher),
            selectinload(Course.enrollments),
            selectinload(Course.schedules),
            selectinload(Course.assignments),
        )
        .order_by(Course.code)
    ).unique().all()

    schedule = [
        StudentScheduleOut(
            course_id=course.id,
            course_code=course.code,
            course_name=course.name,
            teacher_name=course.teacher.name,
            weekday=item.weekday,
            start_time=item.start_time,
            end_time=item.end_time,
            room=item.room,
            timezone=item.timezone or course.timezone,
        )
        for course in courses
        for item in course.schedules
    ]
    schedule.sort(key=lambda item: (item.weekday, item.start_time, item.course_code))

    student_submissions = {
        assignment.id: submission
        for assignment, submission in db.execute(
            select(Assignment, Submission)
            .join(Course, Course.id == Assignment.course_id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .outerjoin(
                Submission,
                and_(
                    Submission.assignment_id == Assignment.id,
                    Submission.student_id == user.id,
                ),
            )
            .where(Enrollment.student_id == user.id)
        ).all()
    }
    now = datetime.now(timezone.utc)
    reminders = []
    for course in courses:
        for assignment in course.assignments:
            if assignment.status != "published":
                continue
            status, submitted_at, score = _submission_status(assignment, student_submissions.get(assignment.id), now)
            reminders.append(
                StudentAssignmentReminderOut(
                    id=assignment.id,
                    course_id=course.id,
                    course_name=course.name,
                    title=assignment.title,
                    due_at=assignment.due_at,
                    max_score=assignment.max_score,
                    submission_status=status,
                    submitted_at=submitted_at,
                    score=score,
                )
            )
    def due_sort_key(item):
        if item.due_at is None:
            return (True, datetime.max.replace(tzinfo=timezone.utc), item.title)
        due_at = item.due_at if item.due_at.tzinfo else item.due_at.replace(tzinfo=timezone.utc)
        return (False, due_at, item.title)

    reminders.sort(key=due_sort_key)

    return StudentDashboardOut(
        timezone=settings.zoom_default_timezone,
        courses=[_serialize_course(course) for course in courses],
        schedule=schedule,
        assignment_reminders=reminders,
    )
