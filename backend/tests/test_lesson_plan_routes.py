"""HTTP-level coverage for the lesson plan routes.

The fixture installs its own database override and restores the previous one so
these tests stay isolated when the whole suite runs in one process.
"""

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.security as security  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def database():
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        db.add_all(
            [
                User(username="teacher", email="teacher@example.test", name="Teacher", password_hash=hash_password("123456"), role=UserRole.teacher),
                User(username="other", email="other@example.test", name="Other", password_hash=hash_password("123456"), role=UserRole.teacher),
                User(username="student", email="student@example.test", name="Student", password_hash=hash_password("123456"), role=UserRole.student),
            ]
        )
        db.commit()
    yield


@pytest.fixture
def client():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app)
    finally:
        if previous is not None:
            app.dependency_overrides[get_db] = previous
        else:
            app.dependency_overrides.pop(get_db, None)


def login(client: TestClient, username: str) -> TestClient:
    response = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert response.status_code == 200
    return client


def _create_project(client: TestClient) -> str:
    response = client.post("/api/lesson-plans/projects", json={"request_text": "中四物理：牛顿第二定律"})
    assert response.status_code == 201
    return response.json()["id"]


def test_student_cannot_reach_the_lesson_plan_surface(client: TestClient):
    login(client, "student")
    assert client.get("/api/lesson-plans/projects").status_code == 403
    assert client.post("/api/lesson-plans/projects", json={"request_text": "x"}).status_code == 403


def test_teacher_creates_project_and_reads_workspace_state(client: TestClient):
    login(client, "teacher")
    project_id = _create_project(client)
    state = client.get(f"/api/lesson-plans/projects/{project_id}/state")
    assert state.status_code == 200
    payload = state.json()
    assert payload["project"]["id"] == project_id
    assert payload["project"]["page_count"] == 0
    assert payload["pages"] == []
    assert payload["messages"] == []
    assert payload["capabilities"]["ai_configured"] is False


def test_chat_stream_ends_with_complete_event(client: TestClient):
    login(client, "teacher")
    project_id = _create_project(client)
    response = client.post(f"/api/lesson-plans/projects/{project_id}/chat/stream", json={"content": "做一份学案"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
    assert any('"type": "status"' in event for event in events)
    assert '"type": "complete"' in events[-1]
    assert '"degraded": true' in events[-1]


def test_generate_and_download_markdown(client: TestClient):
    login(client, "teacher")
    project_id = _create_project(client)
    generated = client.post(f"/api/lesson-plans/projects/{project_id}/generate", json={"page_count": 3, "include_answers": True})
    assert generated.status_code == 200
    body = generated.json()
    assert len(body["pages"]) == 3
    assert body["degraded"] is True
    page_id = body["pages"][0]["id"]

    markdown = client.get(f"/api/lesson-plans/projects/{project_id}/markdown", params={"include_answers": "false"})
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert "attachment" in markdown.headers["content-disposition"]
    assert markdown.text.startswith("# ")
    assert "参考答案" not in markdown.text

    patched = client.patch(
        f"/api/lesson-plans/projects/{project_id}/pages/{page_id}/document",
        json={"document": {"version": 2, "markdown": "- 更新后的目标"}, "revision": body["pages"][0]["revision"]},
    )
    assert patched.status_code == 200
    assert patched.json()["revision"] == body["pages"][0]["revision"] + 1
    conflict = client.patch(
        f"/api/lesson-plans/projects/{project_id}/pages/{page_id}/document",
        json={"document": {"version": 2, "markdown": "x"}, "revision": body["pages"][0]["revision"]},
    )
    assert conflict.status_code == 409


def test_upload_material_is_listed_and_downloadable(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr("app.services.file_processing.orchestration.enqueue_job", lambda *args, **kwargs: None)
    login(client, "teacher")
    project_id = _create_project(client)
    uploaded = client.post(
        f"/api/lesson-plans/projects/{project_id}/files",
        files={"file": ("notes.md", io.BytesIO("# 牛顿第二定律\nF=ma".encode("utf-8")), "text/markdown")},
    )
    assert uploaded.status_code == 201
    asset = uploaded.json()
    assert asset["title"] == "notes.md"
    assert asset["chars"] > 0
    state = client.get(f"/api/lesson-plans/projects/{project_id}/state").json()
    assert len(state["assets"]) == 1
    download = client.get(f"/api/lesson-plans/projects/{project_id}/assets/{asset['id']}")
    assert download.status_code == 200
    assert b"F=ma" in download.content
    removed = client.delete(f"/api/lesson-plans/projects/{project_id}/files/{asset['id']}")
    assert removed.status_code == 200
    assert client.get(f"/api/lesson-plans/projects/{project_id}/state").json()["assets"] == []


def test_pdf_export_downloads_through_stubbed_renderer(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ppt_storage_dir", str(tmp_path / "ppt"))

    def fake_render(html_text, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 stub")

    monkeypatch.setattr("app.services.lesson_plan.service.render_pdf", fake_render)
    login(client, "teacher")
    project_id = _create_project(client)
    client.post(f"/api/lesson-plans/projects/{project_id}/generate", json={"page_count": 2})
    exported = client.post(f"/api/lesson-plans/projects/{project_id}/exports", json={"include_answers": True, "black_white": False})
    assert exported.status_code == 202
    job = exported.json()
    assert job["status"] == "completed"
    status_response = client.get(f"/api/lesson-plans/projects/{project_id}/exports/{job['id']}")
    assert status_response.json()["status"] == "completed"
    download = client.get(f"/api/lesson-plans/projects/{project_id}/exports/{job['id']}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_projects_are_not_visible_to_another_teacher(client: TestClient):
    login(client, "teacher")
    project_id = _create_project(client)

    other = login(TestClient(app), "other")
    assert other.get(f"/api/lesson-plans/projects/{project_id}/state").status_code == 404
    assert other.delete(f"/api/lesson-plans/projects/{project_id}").status_code == 404
