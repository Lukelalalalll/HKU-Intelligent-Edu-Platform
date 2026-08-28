from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models import Assignment, Course, Enrollment, Submission, User, UserRole
from app.schemas import AssignmentCreate, AssignmentOut, SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/api/courses/{course_id}/assignments", tags=["assignments"])

@router.get("", response_model=list[AssignmentOut])
def list_assignments(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")
    if user.role == UserRole.student and not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    return db.scalars(select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.created_at.desc())).all()

@router.post("", response_model=AssignmentOut, status_code=201)
def create_assignment(course_id: str, payload: AssignmentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role != UserRole.admin and course.teacher_id != user.id:
        raise HTTPException(403, "Only the course teacher can publish assignments")
    assignment = Assignment(course_id=course_id, teacher_id=user.id, **payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{assignment_id}/submissions", response_model=SubmissionOut, status_code=201)
def submit_assignment(course_id: str, assignment_id: str, payload: SubmissionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.student:
        raise HTTPException(403, "Only students can submit assignments")
    assignment = db.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id))
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    existing = db.scalar(select(Submission).where(Submission.assignment_id == assignment_id, Submission.student_id == user.id))
    if existing:
        existing.content = payload.content
        existing.file_asset_id = payload.file_asset_id
        db.commit()
        db.refresh(existing)
        return existing
    submission = Submission(assignment_id=assignment_id, student_id=user.id, **payload.model_dump())
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission

@router.get("/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(course_id: str, assignment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment or assignment.course_id != course_id:
        raise HTTPException(404, "Assignment not found")
    if user.role != UserRole.admin and assignment.teacher_id != user.id:
        raise HTTPException(403, "Only the course teacher can view submissions")
    return db.scalars(select(Submission).where(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc())).all()

