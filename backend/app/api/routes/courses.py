from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models import Course, CourseSchedule, Enrollment, User, UserRole
from app.schemas import CourseCreate, CourseOut, ScheduleIn

router = APIRouter(prefix="/api/courses", tags=["courses"])

def serialize(course: Course) -> CourseOut:
    return CourseOut(id=course.id, code=course.code, name=course.name, description=course.description, teacher_id=course.teacher_id, academic_year_start=course.academic_year_start, semester=course.semester, timezone=course.timezone, teacher_name=course.teacher.name, enrolled_count=len(course.enrollments), schedules=[ScheduleIn.model_validate(s, from_attributes=True) for s in course.schedules])

@router.get("", response_model=list[CourseOut])
def list_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.teacher:
        courses = db.scalars(select(Course).where(Course.teacher_id == user.id).order_by(Course.code)).all()
    elif user.role == UserRole.student:
        courses = db.scalars(select(Course).join(Enrollment).where(Enrollment.student_id == user.id).order_by(Course.code)).all()
    else:
        courses = db.scalars(select(Course).order_by(Course.code)).all()
    return [serialize(c) for c in courses]

@router.post("", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    if db.scalar(select(Course).where(Course.code == payload.code.strip().upper())):
        raise HTTPException(status_code=409, detail="Course code already exists")
    course = Course(
        code=payload.code.strip().upper(),
        name=payload.name,
        description=payload.description,
        teacher_id=user.id,
        academic_year_start=payload.academic_year_start,
        semester=payload.semester,
        timezone=payload.timezone,
    )
    course.schedules = [CourseSchedule(**s.model_dump()) for s in payload.schedules]
    db.add(course)
    db.commit()
    db.refresh(course)
    return serialize(course)

@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.student and not any(e.student_id == user.id for e in course.enrollments):
        raise HTTPException(403, "You are not enrolled in this course")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")
    return serialize(course)

@router.post("/{course_id}/enroll", status_code=201)
def enroll(course_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    if not db.get(Course, course_id):
        raise HTTPException(404, "Course not found")
    if db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(409, "Already enrolled")
    db.add(Enrollment(course_id=course_id, student_id=user.id))
    db.commit()
    return {"message": "Enrolled"}

@router.delete("/{course_id}/enroll")
def unenroll(course_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    enrollment = db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id))
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    db.delete(enrollment)
    db.commit()
    return {"message": "Unenrolled"}
