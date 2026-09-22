"""Focused regression tests for the teacher AI teaching video backend.

These tests deliberately keep queue delivery at the outbox boundary.  The API
must commit a durable outbox row before a worker is allowed to run; starting a
real fallback worker in a route test would race the in-memory test database.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.security as security  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Course,
    FileAsset,
    TaskOutbox,
    User,
    UserRole,
    VideoGenerationJob,
    VideoProject,
)
from app.services.video_generation.coze_provider import CozeProvider  # noqa: E402
from app.services.video_generation.local_provider import LocalProvider  # noqa: E402
from app.services.video_generation.schemas import (  # noqa: E402
    VideoGenerationInput,
    normalize_output,
)


ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "123456"}
    )
    assert response.status_code == 200, response.text


def _course_id() -> str:
    with TestingSession() as db:
        return db.scalar(select(Course).where(Course.code == "COMP2119")).id


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    """Reset all models and use the same session factory as each request."""

    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
    app.dependency_overrides[get_db] = override_db

    with TestingSession() as db:
        teacher = User(
            username="teacher",
            email="teacher@example.test",
            name="Teacher",
            password_hash=hash_password("123456"),
            role=UserRole.teacher,
        )
        other = User(
            username="other",
            email="other@example.test",
            name="Other",
            password_hash=hash_password("123456"),
            role=UserRole.teacher,
        )
        student = User(
            username="student",
            email="student@example.test",
            name="Student",
            password_hash=hash_password("123456"),
            role=UserRole.student,
        )
        admin = User(
            username="admin",
            email="admin@example.test",
            name="Admin",
            password_hash=hash_password("123456"),
            role=UserRole.admin,
        )
        db.add_all([teacher, other, student, admin])
        db.flush()
        db.add(
            Course(
                code="COMP2119",
                name="Learning Design",
                description="Demo",
                teacher_id=teacher.id,
            )
        )
        db.commit()

    yield
    app.dependency_overrides.pop(get_db, None)


def test_video_routes_require_teacher_and_scope_projects_to_owner():
    teacher = TestClient(app)
    _login(teacher, "teacher")
    created = teacher.post(
        "/api/teacher/video-projects",
        json={"title": "Owned lesson", "course_id": _course_id(), "input_text": "Intro"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    other = TestClient(app)
    _login(other, "other")
    assert other.get(f"/api/teacher/video-projects/{project_id}").status_code == 404
    assert other.get("/api/teacher/video-projects").json() == []
    assert (
        other.post(
            "/api/teacher/video-projects",
            json={"title": "Cross course", "course_id": _course_id()},
        ).status_code
        == 404
    )

    for username in ("student", "admin"):
        client = TestClient(app)
        _login(client, username)
        assert client.get("/api/teacher/video-projects").status_code == 403
        assert client.post("/api/teacher/video-projects", json={"title": "No"}).status_code == 403


def test_project_source_requires_owned_file_and_preserves_source_text():
    with TestingSession() as db:
        teacher = db.scalar(select(User).where(User.username == "teacher"))
        other = db.scalar(select(User).where(User.username == "other"))
        own_file = FileAsset(
            original_name="notes.pdf",
            mime_type="application/pdf",
            extension="pdf",
            size_bytes=3,
            sha256="a" * 64,
            storage_key="notes.pdf",
            uploader_id=teacher.id,
        )
        other_file = FileAsset(
            original_name="private.pdf",
            mime_type="application/pdf",
            extension="pdf",
            size_bytes=3,
            sha256="b" * 64,
            storage_key="private.pdf",
            uploader_id=other.id,
        )
        db.add_all([own_file, other_file])
        db.commit()
        own_id, other_id = own_file.id, other_file.id

    client = TestClient(app)
    _login(client, "teacher")
    project = client.post("/api/teacher/video-projects", json={"title": "Sources"}).json()
    project_id = project["id"]
    denied = client.post(
        f"/api/teacher/video-projects/{project_id}/sources",
        json={"file_asset_id": other_id, "title": "private"},
    )
    assert denied.status_code == 404
    source = client.post(
        f"/api/teacher/video-projects/{project_id}/sources",
        json={
            "file_asset_id": own_id,
            "source_type": "pdf",
            "title": "Notes",
            "extracted_text": "A source paragraph",
            "metadata": {"page": 1},
        },
    )
    assert source.status_code == 201, source.text
    assert source.json()["extracted_text"] == "A source paragraph"
    assert source.json()["metadata_json"] == {"page": 1}


def test_generate_is_idempotent_and_stages_durable_outbox(monkeypatch):
    staged: list[tuple[str, tuple, str]] = []

    def fake_stage_and_publish(db, kind, args, task_id):
        from app.jobs.dispatcher import stage_task

        stage_task(db, kind, args, task_id)
        db.commit()
        staged.append((kind, args, task_id))
        return task_id

    monkeypatch.setattr("app.api.routes.teacher_video.stage_and_publish", fake_stage_and_publish)
    client = TestClient(app)
    _login(client, "teacher")
    project = client.post("/api/teacher/video-projects", json={"title": "Queue me"}).json()
    payload = {"idempotency_key": "same-request"}
    first = client.post(f"/api/teacher/video-projects/{project['id']}/generate", json=payload)
    second = client.post(f"/api/teacher/video-projects/{project['id']}/generate", json=payload)
    assert first.status_code == 202, first.text
    assert second.status_code == 202, second.text
    assert first.json()["id"] == second.json()["id"]
    assert len(staged) == 1
    with TestingSession() as db:
        job = db.get(VideoGenerationJob, first.json()["id"])
        outbox = db.get(TaskOutbox, staged[0][2])
        assert job is not None and job.status == "queued"
        assert outbox is not None
        assert outbox.task_type == "video_generation"
        assert outbox.payload_json == {"args": [job.id]}


def test_cancel_and_retry_are_owner_scoped_and_enqueue_new_job(monkeypatch):
    calls = []

    def fake_stage_and_publish(db, kind, args, task_id):
        from app.jobs.dispatcher import stage_task

        stage_task(db, kind, args, task_id)
        db.commit()
        calls.append((kind, args, task_id))
        return task_id

    monkeypatch.setattr("app.api.routes.teacher_video.stage_and_publish", fake_stage_and_publish)
    client = TestClient(app)
    _login(client, "teacher")
    project = client.post("/api/teacher/video-projects", json={"title": "Retry me"}).json()
    generated = client.post(
        f"/api/teacher/video-projects/{project['id']}/generate",
        json={"idempotency_key": "cancel-me"},
    ).json()
    canceled = client.post(
        f"/api/teacher/video-projects/{project['id']}/jobs/{generated['id']}/cancel"
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    retried = client.post(
        f"/api/teacher/video-projects/{project['id']}/jobs/{generated['id']}/retry"
    )
    assert retried.status_code == 202, retried.text
    assert retried.json()["id"] != generated["id"]
    assert retried.json()["status"] == "queued"
    assert retried.json()["idempotency_key"] == "cancel-me:retry:1"
    assert len(calls) == 2

    other = TestClient(app)
    _login(other, "other")
    assert other.post(
        f"/api/teacher/video-projects/{project['id']}/jobs/{generated['id']}/cancel"
    ).status_code == 404


def test_normalize_output_accepts_coze_aliases_and_rejects_invalid_scenes():
    output = normalize_output(
        {
            "text": "Script",
            "run_id": "run-42",
            "subtitle_url": "https://example.test/captions.vtt",
            "scenes": [
                {
                    "order_index": 2,
                    "duration": 8,
                    "voiceover": "Speak",
                    "on_screen_text": "Read",
                    "assets": ["https://example.test/a.png"],
                }
            ],
        }
    )
    assert output.script == "Script"
    assert output.provider_job_id == "run-42"
    assert output.captions_url.endswith("captions.vtt")
    assert output.scenes[0].order == 2
    assert output.scenes[0].narration == "Speak"
    assert output.scenes[0].onscreen_text == "Read"
    assert output.scenes[0].asset_urls == ["https://example.test/a.png"]
    with pytest.raises(ValueError, match="场景 1"):
        normalize_output({"scenes": ["not-an-object"]})


class _Response:
    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._body


class _HttpClient:
    def __init__(self):
        self.posts = []

    def post(self, path, **kwargs):
        self.posts.append((path, kwargs))
        return _Response({"run_id": "run-1"}, headers={"x-request-id": "request-1"})

    def get(self, path, **kwargs):
        assert path == "/v1/workflow/runs/run-1"
        return _Response(
            {
                "status": "success",
                "output": json.dumps(
                    {
                        "script": "A script",
                        "scenes": [{"order": 1, "narration": "A scene", "duration": 4}],
                    }
                ),
            }
        )


def _coze_config(**overrides):
    values = dict(
        coze_enabled=True,
        coze_api_token="server-secret-token",
        coze_workflow_id="workflow-1",
        coze_bot_id="",
        coze_api_base_url="https://coze.example.test",
        coze_timeout_seconds=5,
        coze_poll_interval_seconds=0,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_coze_async_adapter_normalizes_json_and_never_exposes_token_in_errors():
    http = _HttpClient()
    provider = CozeProvider(config=_coze_config(), client=http)
    request = VideoGenerationInput(project_id="p", title="Lesson", source_text="body")
    output = provider.run_generation(request)
    assert output.provider_job_id == "run-1"
    assert output.script == "A script"
    assert output.scenes[0].narration == "A scene"
    assert http.posts[0][1]["headers"]["Authorization"] == "Bearer server-secret-token"
    assert provider.last_request_id == "request-1"

    with pytest.raises(ValueError, match="无法解析") as exc:
        provider.parse_json_content("not JSON")
    assert "server-secret-token" not in str(exc.value)


def test_coze_stream_events_and_malformed_json_are_provider_neutral():
    message = SimpleNamespace(
        event=SimpleNamespace(value="MESSAGE"),
        message=SimpleNamespace(content='{"script":" streamed ","scenes":[]}'),
    )
    done = SimpleNamespace(event=SimpleNamespace(value="DONE"))
    provider = CozeProvider(config=_coze_config())
    provider._coze = SimpleNamespace(
        workflows=SimpleNamespace(
            runs=SimpleNamespace(stream=lambda **_: [message, done])
        )
    )
    events = list(
        provider.stream_generation(VideoGenerationInput(project_id="p", title="Lesson"))
    )
    assert [event["type"] for event in events] == ["message", "complete"]
    assert events[-1]["output"]["script"].strip() == "streamed"

    bad_message = SimpleNamespace(
        event=SimpleNamespace(value="MESSAGE"),
        message=SimpleNamespace(content="not-json"),
    )
    provider._coze = SimpleNamespace(
        workflows=SimpleNamespace(
            runs=SimpleNamespace(stream=lambda **_: [bad_message, done])
        )
    )
    bad_events = list(
        provider.stream_generation(VideoGenerationInput(project_id="p", title="Lesson"))
    )
    assert bad_events[-1]["type"] == "error"
    assert "无法解析" in bad_events[-1]["detail"]
    assert bad_events[-1]["raw_response"] == "not-json"


def test_local_provider_writes_script_captions_and_srt_without_ffmpeg(tmp_path, monkeypatch):
    config = SimpleNamespace(
        local_video_enabled=True,
        local_video_model_dir="",
        local_video_width=640,
        local_video_height=360,
        local_video_fps=12,
        local_video_tts_command="",
        local_video_tts_timeout_seconds=1,
        video_storage_path=tmp_path,
    )
    monkeypatch.setattr("app.services.video_generation.local_provider.shutil.which", lambda _: None)
    provider = LocalProvider(config=config)
    output = provider.run_generation(
        VideoGenerationInput(project_id="p", title="Cards", source_text="Narration", duration_seconds=15)
    )
    paths = provider.render(output, "job-1")
    assert Path(paths["script"]).read_text(encoding="utf-8") == "Narration"
    assert "WEBVTT" in Path(paths["captions"]).read_text(encoding="utf-8")
    assert "-->" in Path(paths["srt"]).read_text(encoding="utf-8")
    assert paths["video"] == ""
    assert paths["audio"] == ""


def test_recover_outbox_republishes_unpublished_rows(monkeypatch):
    from app.jobs import dispatcher

    with TestingSession() as db:
        db.add(
            TaskOutbox(
                id="video-generation:recover",
                task_type="video_generation",
                payload_json={"args": ["job-1"]},
                status="pending",
            )
        )
        db.commit()

    published = []
    monkeypatch.setattr("app.db.session.SessionLocal", TestingSession)
    monkeypatch.setattr(
        dispatcher,
        "dispatch",
        lambda kind, *args, task_id=None: published.append((kind, args, task_id)) or "broker-1",
    )
    dispatcher.recover_outbox()
    assert published == [("video_generation", ("job-1",), "video-generation:recover")]
    with TestingSession() as db:
        row = db.get(TaskOutbox, "video-generation:recover")
        assert row.status == "published"
        assert row.attempts == 1

