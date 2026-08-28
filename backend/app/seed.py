from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Assignment, Course, CourseSchedule, Enrollment, User, UserRole

def get_or_create_user(db, username: str, email: str, name: str, role: UserRole):
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        user = User(username=username, email=email, name=name, password_hash=hash_password("123456"), role=role)
        db.add(user)
        db.flush()
    return user

def seed():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        student = get_or_create_user(db, "demo_student", "demo_student@example.test", "Demo Student", UserRole.student)
        teacher = get_or_create_user(db, "demo_teacher", "demo_teacher@example.test", "Demo Teacher", UserRole.teacher)
        get_or_create_user(db, "demo_admin", "demo_admin@example.test", "Demo Admin", UserRole.admin)
        course = db.scalar(select(Course).where(Course.code == "HKU-AI-101"))
        if not course:
            course = Course(code="HKU-AI-101", name="AI-Supported Learning", description="Phase 1 demonstration course", teacher_id=teacher.id)
            course.schedules = [CourseSchedule(weekday=2, start_time="10:00", end_time="12:00", room="CPD-LG.09")]
            db.add(course)
            db.flush()
        if not db.scalar(select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.student_id == student.id)):
            db.add(Enrollment(course_id=course.id, student_id=student.id))
        if not db.scalar(select(Assignment).where(Assignment.course_id == course.id)):
            db.add(Assignment(course_id=course.id, teacher_id=teacher.id, title="RAG Learning Reflection", description="Write a short reflection on how AI can support learning.", max_score=100))
        db.commit()
        print("Seed complete: demo_student, demo_teacher, demo_admin / 123456")

if __name__ == "__main__":
    seed()

