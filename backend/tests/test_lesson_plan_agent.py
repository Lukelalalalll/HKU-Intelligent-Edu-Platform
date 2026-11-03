"""Service-level coverage for the lesson plan agent workflow.

The tests run against SQLite and deliberately exercise the deterministic
fallback path: that path must work on a clean checkout where no AI provider key
has been configured yet.
"""

import io
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.security as security  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models import LessonPlanAsset, LessonPlanPage, LessonPlanProject, User, UserRole  # noqa: E402
from app.services.lesson_plan import LessonPlanService  # noqa: E402
from app.services.lesson_plan import service as service_module  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine, autoflush=False)


def setup_function():
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _teacher(db, username="lesson_teacher"):
    user = User(username=username, email=f"{username}@example.test", name="Lesson Teacher", password_hash="x", role=UserRole.teacher)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class FakeGateway:
    """Gateway double that records the prompt payloads it receives."""

    def __init__(self, data=None):
        self.data = data or {}
        self.calls = []

    def json(self, system, payload):
        self.calls.append((system, payload))
        return self.data

    def stream_json(self, system, payload):
        self.calls.append((system, payload))
        yield {"type": "chunk", "chunk": "正在整理"}
        yield {"type": "final", "data": self.data}


def _project(db, user):
    return LessonPlanService(db, user).create("", "中四物理：牛顿第二定律，45 分钟", None)


def test_capabilities_report_unconfigured_model():
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        capabilities = service.capabilities()
        assert capabilities["ai_configured"] is False
        assert capabilities["model"] is None


def test_fallback_interview_asks_every_topic_then_becomes_ready():
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        questions = []
        result = None
        for index in range(7):
            result = service.interview(project["id"], f"回答 {index}")
            if result["question"]:
                questions.append(result["question"]["code"])
        assert questions == ["grade", "subject", "objectives", "duration", "activities", "page_count"]
        assert result is not None
        assert result["ready_to_generate"] is True
        assert result["degraded"] is True
        state = service.state(project["id"])
        assert state["project"]["current_stage"] == "ready"
        assert len(state["messages"]) == 14


def test_interview_merges_model_answers_and_passes_materials(monkeypatch):
    with Session() as db:
        user = _teacher(db)
        service = LessonPlanService(db, user)
        project = service.create("", "牛顿第二定律", None)
        db.add(
            LessonPlanAsset(
                project_id=project["id"],
                title="textbook.md",
                source_type="upload",
                metadata_json={"text": "牛顿第二定律：F=ma，适用于惯性参考系。", "chars": 22},
            )
        )
        db.commit()
        gateway = FakeGateway(
            {
                "assistant_markdown": "我读到了教材中关于 F=ma 的说明。想先确认学段。",
                "brief_summary": "中四物理，牛顿第二定律",
                "question": {"code": "grade", "label": "面向哪个年级？", "options": ["中四", "中五"]},
                "answers_patch": {"grade": "中四", "subject": "物理", "duration_minutes": 45},
                "missing_fields": ["objectives"],
                "ready_to_generate": False,
                "suggested_additions": ["补充实验活动"],
            }
        )
        monkeypatch.setattr(LessonPlanService, "_gateway", lambda self: gateway)
        result = service.interview(project["id"], "做一份牛顿第二定律学案")
        assert result["degraded"] is False
        assert result["answers"]["grade"] == "中四"
        assert result["brief_summary"] == "中四物理，牛顿第二定律"
        assert result["question"]["options"] == ["中四", "中五"]
        system_prompt, payload = gateway.calls[0]
        assert "学案 Agent" in system_prompt
        assert payload["materials"][0]["title"] == "textbook.md"
        assert "F=ma" in payload["materials"][0]["excerpt"]


def test_stream_interview_terminates_with_complete_when_provider_missing():
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        events = list(service.interview_stream(project["id"], "做一份学案"))
        assert events[-1]["type"] == "complete"
        assert events[-1]["result"]["degraded"] is True
        assert events[-1]["result"]["question"]["code"] == "grade"


def test_generation_replaces_pages_instead_of_appending():
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        first = service.generate(project["id"], page_count=4)
        assert first["degraded"] is True
        assert len(first["pages"]) == 4
        # Trimming keeps practice ahead of the activity page.
        roles = [page["page_role"] for page in first["pages"]]
        assert "exercise" in roles and "objectives" in roles and "summary" in roles
        assert first["project"]["current_stage"] == "outline"
        second = service.generate(project["id"], page_count=3)
        assert len(second["pages"]) == 3
        assert db.scalar(select(LessonPlanPage).where(LessonPlanPage.project_id == project["id"]).order_by(LessonPlanPage.sort_order)) is not None
        assert len(db.scalars(select(LessonPlanPage).where(LessonPlanPage.project_id == project["id"])).all()) == 3
        marks = [page["markdown"] for page in second["pages"]]
        assert all(mark for mark in marks)


def test_generation_uses_model_json_and_updates_title(monkeypatch):
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        gateway = FakeGateway(
            {
                "title": "牛顿第二定律：从实验到应用",
                "subject": "物理",
                "grade": "中四",
                "duration_minutes": 45,
                "summary_markdown": "共 2 页，适合一节 45 分钟课堂。",
                "pages": [
                    {"title": "学习目标", "page_role": "objectives", "markdown": "## 学习目标\n\n- 理解 F=ma"},
                    {"title": "课堂练习", "page_role": "exercise", "markdown": "1. 计算题\n\n> [!answer] 参考答案\n> a=2"},
                ],
            }
        )
        monkeypatch.setattr(LessonPlanService, "_gateway", lambda self: gateway)
        result = service.generate(project["id"], page_count=2)
        assert result["degraded"] is False
        assert len(result["pages"]) == 2
        assert result["pages"][0]["markdown"].startswith("- 理解")  # duplicate title heading removed
        # The auto title is replaced by the model title once generation succeeds.
        current = db.get(LessonPlanProject, project["id"])
        assert current.title == "牛顿第二定律：从实验到应用"


def test_patch_page_rejects_stale_revision_and_bumps_on_success():
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        generated = service.generate(project["id"], page_count=2)
        page = generated["pages"][0]
        updated = service.patch_page(project["id"], page["id"], {"version": 2, "markdown": "- 新目标"}, page["revision"])
        assert updated["revision"] == page["revision"] + 1
        assert updated["status"] == "edited"
        assert updated["markdown"] == "- 新目标"
        with pytest.raises(HTTPException) as excinfo:
            service.patch_page(project["id"], page["id"], {"version": 2, "markdown": "x"}, page["revision"])
        assert excinfo.value.status_code == 409


def test_refine_turn_updates_pages_through_model(monkeypatch):
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        generated = service.generate(project["id"], page_count=3)
        page = generated["pages"][1]
        gateway = FakeGateway(
            {
                "assistant_markdown": "已把练习难度提高。",
                "page_updates": [{"page_id": page["id"], "markdown": "1. 更难的练习"}],
                "needs_regenerate": False,
            }
        )
        monkeypatch.setattr(LessonPlanService, "_gateway", lambda self: gateway)
        result = service.interview(project["id"], "练习再难一点")
        assert result["mode"] == "refine"
        assert result["page_updates"] == [page["id"]]
        refreshed = service._page(project["id"], page["id"])
        assert refreshed.document_json["markdown"] == "1. 更难的练习"
        assert refreshed.revision == page["revision"] + 1


def test_upload_extracts_text_and_exposes_prompt_context(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr("app.services.file_processing.orchestration.enqueue_job", lambda *args, **kwargs: None)
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        upload = UploadFile(
            file=io.BytesIO("# 教材笔记\n牛顿第二定律 F=ma".encode("utf-8")),
            filename="notes.md",
            headers=Headers({"content-type": "text/markdown"}),
        )
        asset = service.add_file(project["id"], upload)
        assert asset["title"] == "notes.md"
        assert asset["chars"] > 0
        state = service.state(project["id"])
        assert len(state["assets"]) == 1
        from app.services.lesson_plan.files import context_materials

        materials = context_materials(db, service.project(project["id"]))
        assert materials[0]["title"] == "notes.md"
        assert "F=ma" in materials[0]["text"]


def test_export_pdf_records_job_and_markdown_filters_answers(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ppt_storage_dir", str(tmp_path / "ppt"))
    with Session() as db:
        service = LessonPlanService(db, _teacher(db))
        project = service.create("", "牛顿第二定律", None)
        service.generate(project["id"], page_count=4)

        def fake_render(html_text, output_path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setattr(service_module, "render_pdf", fake_render)
        job = service.export_pdf(project["id"], include_answers=True, black_white=True)
        assert job["status"] == "completed"
        assert service.export_path(project["id"], job["id"]).read_bytes().startswith(b"%PDF")
        assert service.project(project["id"]).current_stage == "exported"

        filename, content = service.export_markdown(project["id"], include_answers=False)
        assert filename.endswith(".md")
        text = content.decode("utf-8")
        assert text.startswith("# ")
        assert "参考答案" not in text


def test_projects_are_scoped_to_their_owner():
    with Session() as db:
        owner = _teacher(db, "owner_teacher")
        other = _teacher(db, "other_teacher")
        project = LessonPlanService(db, owner).create("", "牛顿第二定律", None)
        with pytest.raises(HTTPException) as excinfo:
            LessonPlanService(db, other).project(project["id"])
        assert excinfo.value.status_code == 404
