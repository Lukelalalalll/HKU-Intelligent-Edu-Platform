from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Assignment, Course, CourseSchedule, Submission, User, UserRole
from app.schemas import (
    CourseOut,
    PendingAssignmentOut,
    ScheduleIn,
    TeacherDashboardOut,
    TeacherScheduleOut,
)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def serialize_course(course: Course) -> CourseOut:
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
        schedules=[ScheduleIn.model_validate(s, from_attributes=True) for s in course.schedules],
    )


@router.get("/dashboard", response_model=TeacherDashboardOut)
def teacher_dashboard(
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    courses = db.scalars(
        select(Course)
        .where(Course.teacher_id == user.id)
        .options(selectinload(Course.teacher), selectinload(Course.enrollments), selectinload(Course.schedules))
        .order_by(Course.code)
    ).all()
    course_ids = [course.id for course in courses]

    schedule_rows = db.execute(
        select(CourseSchedule, Course.code, Course.name)
        .join(Course, Course.id == CourseSchedule.course_id)
        .where(CourseSchedule.course_id.in_(course_ids) if course_ids else False)
        .order_by(CourseSchedule.weekday, CourseSchedule.start_time)
    ).all()
    schedule = [
        TeacherScheduleOut(
            course_id=item.course_id,
            course_code=code,
            course_name=name,
            weekday=item.weekday,
            start_time=item.start_time,
            end_time=item.end_time,
            room=item.room,
        )
        for item, code, name in schedule_rows
    ]

    pending_rows = db.execute(
        select(Assignment, Course.name, func.count(Submission.id).label("pending_count"))
        .join(Course, Course.id == Assignment.course_id)
        .outerjoin(
            Submission,
            and_(Submission.assignment_id == Assignment.id, Submission.score.is_(None)),
        )
        .where(Assignment.teacher_id == user.id)
        .group_by(Assignment.id, Course.name)
        .order_by(Assignment.due_at.asc().nullslast(), Assignment.created_at.desc())
    ).all()
    pending = [
        PendingAssignmentOut(
            id=assignment.id,
            course_id=assignment.course_id,
            title=assignment.title,
            description=assignment.description,
            due_at=assignment.due_at,
            max_score=assignment.max_score,
            status=assignment.status,
            course_name=course_name,
            pending_count=int(pending_count),
        )
        for assignment, course_name, pending_count in pending_rows
        if pending_count
    ]
    return TeacherDashboardOut(
        courses=[serialize_course(course) for course in courses],
        schedule=schedule,
        pending_assignments=pending,
    )
