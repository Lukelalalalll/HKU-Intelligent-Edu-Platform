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
        demo_courses = [
            ("HKU-AI-101", "AI-Supported Learning", "Design learning experiences with responsible AI.", 2025, "summer", 2, "10:00", "12:00", "CPD-LG.09"),
            ("HKU-EDU-201", "Learning Analytics Studio", "Read learner signals and turn them into action.", 2025, "semester_2", 4, "14:00", "16:00", "MB-201"),
            ("HKU-DES-110", "Digital Learning Design", "A studio course for clear, inclusive online teaching.", 2025, "semester_1", 1, "09:00", "11:00", "Run Run Shaw Tower"),
            ("HKU-EDU-305", "Assessment for Learning", "Build feedback loops that help every learner progress.", 2024, "semester_2", 3, "13:00", "15:00", "MB-301"),
        ]
        for code, name, description, year, semester, weekday, start_time, end_time, room in demo_courses:
            course = db.scalar(select(Course).where(Course.code == code))
            if not course:
                course = Course(code=code, name=name, description=description, teacher_id=teacher.id, academic_year_start=year, semester=semester)
                course.schedules = [CourseSchedule(weekday=weekday, start_time=start_time, end_time=end_time, room=room)]
                db.add(course)
                db.flush()
            if not db.scalar(select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.student_id == student.id)):
                db.add(Enrollment(course_id=course.id, student_id=student.id))
            if not db.scalar(select(Assignment).where(Assignment.course_id == course.id)):
                db.add(Assignment(course_id=course.id, teacher_id=teacher.id, title=f"{name} Reflection", description="Write a short reflection on this week's learning.", max_score=100))
        db.commit()
        print("Seed complete: demo_student, demo_teacher, demo_admin / 123456")

if __name__ == "__main__":
    seed()
