import sys
from pathlib import Path

from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.security as security
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models import Course, Enrollment, User, UserRole


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


_previous_override = None


def setup_function():
    global _previous_override
    _previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        teacher = User(username="teacher", email="teacher@example.test", name="Teacher", password_hash=hash_password("123456"), role=UserRole.teacher)
        student = User(username="student", email="student@example.test", name="Student", password_hash=hash_password("123456"), role=UserRole.student)
        other = User(username="other", email="other@example.test", name="Other", password_hash=hash_password("123456"), role=UserRole.student)
        db.add_all([teacher, student, other]); db.flush()
        course = Course(code="COMP2119", name="Learning Design", teacher_id=teacher.id)
        db.add(course); db.flush(); db.add(Enrollment(course_id=course.id, student_id=student.id)); db.commit()


def teardown_function():
    if _previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = _previous_override


def login(client: TestClient, username: str):
    response = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert response.status_code == 200


def course_id() -> str:
    with TestingSession() as db:
        return db.query(Course).filter_by(code="COMP2119").one().id


def test_discussion_is_course_scoped_and_supports_reply_and_likes():
    student = TestClient(app); login(student, "student")
    other = TestClient(app); login(other, "other")
    cid = course_id()

    assert other.get(f"/api/courses/{cid}/discussion").status_code == 403
    created = student.post(f"/api/courses/{cid}/discussion", json={"content": "  A useful question  "})
    assert created.status_code == 201
    comment = created.json()
    assert comment["content"] == "A useful question"
    assert comment["course_id"] == cid
    assert comment["author"]["username"] == "student"

    reply = student.post(f"/api/courses/{cid}/discussion/{comment['id']}/replies", json={"content": "A useful answer"})
    assert reply.status_code == 201
    assert student.post(f"/api/courses/{cid}/discussion/{reply.json()['id']}/replies", json={"content": "Nested"}).status_code == 400

    assert student.put(f"/api/courses/{cid}/discussion/{comment['id']}/like").json() == {"liked": True, "like_count": 1}
    assert student.put(f"/api/courses/{cid}/discussion/{comment['id']}/like").json() == {"liked": True, "like_count": 1}
    assert student.delete(f"/api/courses/{cid}/discussion/{comment['id']}/like").json() == {"liked": False, "like_count": 0}

    listed = student.get(f"/api/courses/{cid}/discussion")
    assert listed.status_code == 200
    assert listed.json()[0]["replies"][0]["content"] == "A useful answer"
    assert listed.json()[0]["liked_by_me"] is False


def test_discussion_delete_is_limited_to_author_or_course_teacher():
    student = TestClient(app); login(student, "student")
    other = TestClient(app); login(other, "other")
    teacher = TestClient(app); login(teacher, "teacher")
    cid = course_id()
    comment = student.post(f"/api/courses/{cid}/discussion", json={"content": "Delete me"}).json()
    assert student.post(f"/api/courses/{cid}/discussion/{comment['id']}/replies", json={"content": "Reply to delete"}).status_code == 201
    assert other.delete(f"/api/courses/{cid}/discussion/{comment['id']}").status_code == 403
    assert teacher.delete(f"/api/courses/{cid}/discussion/{comment['id']}").status_code == 204
    assert teacher.get(f"/api/courses/{cid}/discussion").json() == []
