import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
import app.core.security as security  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AgentMessage, Assignment, Course, CourseSchedule, Enrollment, Submission, User, UserRole  # noqa: E402
from app.core.config import settings  # noqa: E402


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db


def setup_function():
    # Keep route tests independent of the optional bcrypt wheel available locally.
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        teacher = User(username="teacher", email="teacher@example.test", name="Teacher", password_hash=hash_password("123456"), role=UserRole.teacher)
        other = User(username="other", email="other@example.test", name="Other", password_hash=hash_password("123456"), role=UserRole.teacher)
        student = User(username="student", email="student@example.test", name="Student", password_hash=hash_password("123456"), role=UserRole.student)
        db.add_all([teacher, other, student]); db.flush()
        course = Course(code="COMP2119", name="Learning Design", description="Demo", teacher_id=teacher.id)
        course.schedules = [CourseSchedule(weekday=2, start_time="10:00", end_time="12:00", room="CPD")]
        db.add(course); db.flush()
        db.add(Enrollment(course_id=course.id, student_id=student.id))
        assignment = Assignment(course_id=course.id, teacher_id=teacher.id, title="Reflection", due_at=datetime.now(timezone.utc), max_score=100)
        db.add(assignment); db.flush()
        db.add(Submission(assignment_id=assignment.id, student_id=other.id, content="pending"))
        db.commit()


def login(client: TestClient, username: str):
    response = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert response.status_code == 200


def test_teacher_dashboard_aggregates_schedule_and_pending_reviews():
    client = TestClient(app)
    login(client, "teacher")
    response = client.get("/api/teacher/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["courses"][0]["code"] == "COMP2119"
    assert payload["schedule"][0]["room"] == "CPD"
    assert payload["pending_assignments"][0]["pending_count"] == 1


def test_student_dashboard_is_scoped_and_reports_assignment_status():
    client = TestClient(app)
    login(client, "student")
    response = client.get("/api/student/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["timezone"] == "Asia/Hong_Kong"
    assert [course["code"] for course in payload["courses"]] == ["COMP2119"]
    assert payload["schedule"][0]["course_code"] == "COMP2119"
    assert payload["assignment_reminders"][0]["submission_status"] == "overdue"

    teacher_client = TestClient(app)
    login(teacher_client, "teacher")
    forbidden = teacher_client.get("/api/student/dashboard")
    assert forbidden.status_code == 403


def test_isolated_sessions_do_not_share_host_cookie():
    teacher_client = TestClient(app)
    student_client = TestClient(app)
    isolated = {"X-HKU-Session-Mode": "isolated"}

    teacher_login = teacher_client.post("/api/auth/login", headers=isolated, json={"username": "teacher", "password": "123456"})
    student_login = student_client.post("/api/auth/login", headers=isolated, json={"username": "student", "password": "123456"})
    assert teacher_login.status_code == 200
    assert student_login.status_code == 200

    teacher_headers = {**isolated, "Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    student_headers = {**isolated, "Authorization": f"Bearer {student_login.json()['access_token']}"}
    assert teacher_client.get("/api/teacher/dashboard", headers=teacher_headers).status_code == 200
    assert student_client.get("/api/teacher/dashboard", headers=student_headers).status_code == 403
    assert teacher_client.get("/api/teacher/dashboard", headers=isolated).status_code == 401


def test_agent_conversations_are_isolated_and_cascade_messages_on_delete():
    client = TestClient(app)
    login(client, "teacher")
    created = client.post("/api/agent/conversations", json={"title": "新对话"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert client.post(f"/api/agent/conversations/{conversation_id}/messages", json={"role": "user", "content": "hello"}).status_code == 201
    assert len(client.get(f"/api/agent/conversations/{conversation_id}").json()["messages"]) == 1
    client.delete(f"/api/agent/conversations/{conversation_id}")
    assert client.get(f"/api/agent/conversations/{conversation_id}").status_code == 404
    with TestingSession() as db:
        assert db.query(AgentMessage).filter(AgentMessage.conversation_id == conversation_id).count() == 0

    other_client = TestClient(app)
    login(other_client, "other")
    assert other_client.get(f"/api/agent/conversations/{conversation_id}").status_code == 404


def test_course_materials_are_scoped_and_downloadable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    client = TestClient(app)
    login(client, "teacher")
    with TestingSession() as db:
        course_id = db.query(Course).filter_by(code="COMP2119").one().id

    chapter = client.post(f"/api/courses/{course_id}/materials/chapters", json={"kind": "lecture", "title": "Week 1"})
    assert chapter.status_code == 201
    chapter_id = chapter.json()["id"]
    uploaded = client.post(f"/api/courses/{course_id}/materials/chapters/{chapter_id}/files", files={"file": ("slides.pdf", b"notes", "application/pdf")})
    assert uploaded.status_code == 201
    material_id = uploaded.json()["id"]

    student = TestClient(app)
    login(student, "student")
    listed = student.get(f"/api/courses/{course_id}/materials", params={"kind": "lecture"})
    assert listed.status_code == 200
    assert listed.json()[0]["materials"][0]["file_name"] == "slides.pdf"
    assert student.get(f"/api/courses/{course_id}/materials/{material_id}/download").content == b"notes"

    other = TestClient(app)
    login(other, "other")
    assert other.get(f"/api/courses/{course_id}/materials", params={"kind": "lecture"}).status_code == 403
    assert client.delete(f"/api/courses/{course_id}/materials/chapters/{chapter_id}").status_code == 200
    assert not list(tmp_path.iterdir())
