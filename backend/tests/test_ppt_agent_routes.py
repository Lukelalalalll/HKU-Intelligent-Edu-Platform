import sys
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.security as security  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models import PptAgentEvent, PptDocumentVersion, PptPage, PptProject, PptRequirement, User, UserRole  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.ppt_agent import PptAgentService, decrypt_api_key, encrypt_api_key  # noqa: E402
from app.services.ppt_edit_agent import PptEditAgent  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def setup_function():
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_ppt_project_and_provider_crypto():
    with Session() as db:
        user = User(username="ppt_teacher", email="ppt@example.test", name="PPT Teacher", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        project = PptAgentService(db, user).create_project("课堂设计", "为大一学生制作可持续设计课件")
        assert project["current_stage"] == "init"
        assert len(PptAgentService(db, user).list_messages(project["id"])) == 2
        encrypted = encrypt_api_key("sk-test-key")
        assert encrypted != "sk-test-key"
        assert decrypt_api_key(encrypted) == "sk-test-key"


def test_project_cover_preview_uses_first_page_and_delete_cleans_files(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ppt_storage_dir", str(tmp_path))
    with Session() as db:
        user = User(username="cover_teacher", email="cover@example.test", name="Cover", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        service = PptAgentService(db, user)
        project = service.create_project("封面测试", "制作封面测试课件")
        assert service.list_projects()[0]["cover_preview_url"] is None
        page = PptPage(project_id=project["id"], sort_order=0, title="首页标题", bullets_json=["第一要点"])
        db.add(page)
        db.commit(); db.refresh(db.get(PptProject, project["id"]))
        listed = service.list_projects()[0]
        assert listed["cover_preview_url"] == f"/api/ppt/projects/{project['id']}/pages/{page.id}/preview.svg"
        project_root = settings.ppt_storage_path / project["id"]
        project_root.mkdir(parents=True)
        (project_root / "source.md").write_text("资料", encoding="utf-8")
        export_path = settings.ppt_storage_path / f"{project['id']}.pptx"
        export_path.write_bytes(b"ppt")
        service.delete_project(project["id"])
        assert db.get(PptProject, project["id"]) is None
        assert not project_root.exists()
        assert not export_path.exists()


def test_ppt_generation_requires_model_key():
    with Session() as db:
        user = User(username="ppt_teacher", email="ppt@example.test", name="PPT Teacher", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        project = PptAgentService(db, user).create_project("测试", "测试课件")
        PptAgentService(db, user).requirement_chat(project["id"], "大一学生，50分钟，讲清核心概念，10页，简洁学术风格")
        req = db.scalar(select(PptRequirement).where(PptRequirement.project_id == project["id"]))
        req.status = "ready"; db.commit()
        try:
            PptAgentService(db, user).generate_outline(project["id"], 6, "hku_academic")
        except Exception as exc:
            assert "API Key" in str(exc)
        else:
            raise AssertionError("generation should require a configured model key")


def test_requirement_chat_is_project_and_teacher_scoped(monkeypatch):
    with Session() as db:
        teacher = User(username="teacher_one", email="one@example.test", name="One", password_hash=hash_password("123456"), role=UserRole.teacher)
        other = User(username="teacher_two", email="two@example.test", name="Two", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add_all([teacher, other]); db.commit(); db.refresh(teacher); db.refresh(other)
        project = PptAgentService(db, teacher).create_project("测试", "制作课程课件")

        def fake_json(self, system, payload):
            return {"assistant_markdown": "信息完整，可以生成大纲。", "question": None, "answers_patch": {"audience": "本科生", "duration": "50分钟"}, "missing_fields": [], "ready_to_outline": True, "suggested_additions": ["加入案例"], "page_count_target": 10, "style_preset": "hku_academic"}

        monkeypatch.setattr("app.services.ppt_agent.ProviderGateway.json", fake_json)
        result = PptAgentService(db, teacher).requirement_chat(project["id"], option_id="本科生", option_label="本科生")
        assert result["ready_to_outline"] is True
        assert result["status"] == "ready"
        assert PptAgentService(db, teacher).requirements(project["id"])["answers"]["audience"] == "本科生"
        try:
            PptAgentService(db, other).list_messages(project["id"])
        except Exception as exc:
            assert "不存在" in str(exc)
        else:
            raise AssertionError("another teacher must not access this project")


def test_theme_to_design_auto_assigns_and_creates_documents(monkeypatch):
    with Session() as db:
        user = User(username="layout_teacher", email="layout@example.test", name="Layout", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        service = PptAgentService(db, user)
        project = service.create_project("智能排版", "制作一套课程课件")
        db.add_all([
            PptPage(project_id=project["id"], section_title="导入", sort_order=0, title="课程目标", bullets_json=["理解核心概念"]),
            PptPage(project_id=project["id"], section_title="核心内容", sort_order=1, title="概念比较", bullets_json=["A", "B", "C", "D", "E"]),
        ]); db.commit()
        service.select_theme(project["id"], "light-academic")

        def fake_json(self, system, payload):
            if "版式总监" in system:
                return {"assignments": {payload["outline"][1]["id"]: "two-column"}}
            return {"layout": payload["layout"]["id"], "elements": [{"type": "title", "x": 8, "y": 8, "w": 80, "h": 12, "text": payload["page"]["title"]}]}

        monkeypatch.setattr("app.services.ppt_agent.ProviderGateway.json", fake_json)
        result = service.generate_design(project["id"])
        assert result["project"]["design_status"] == "ready"
        assert set(result["assignments"]) == {page.id for page in db.query(PptPage).filter_by(project_id=project["id"]).all()}
        assert all(page["document"]["elements"] for page in result["pages"])
        events = [event.event_type for event in db.query(PptAgentEvent).filter_by(project_id=project["id"]).all()]
        assert "design.pipeline.started" in events and "design.completed" in events
        service.select_theme(project["id"], "dark")
        assert db.query(PptDocumentVersion).filter_by(project_id=project["id"]).count() == 0
        assert all(page.design_document_json is None for page in db.query(PptPage).filter_by(project_id=project["id"]).all())


def test_preview_agent_can_save_insert_and_delete_slides():
    with Session() as db:
        user = User(username="edit_teacher", email="edit@example.test", name="Edit", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        service = PptAgentService(db, user)
        project = service.create_project("编辑", "制作课件")
        db.add_all([
            PptPage(project_id=project["id"], section_title="导入", sort_order=0, title="第一页", bullets_json=["A"]),
            PptPage(project_id=project["id"], section_title="主体", sort_order=1, title="第二页", bullets_json=["B"]),
        ]); db.commit()
        agent = PptEditAgent(service)
        first = sorted(service.project(project["id"]).pages, key=lambda item: item.sort_order)[0]
        first.design_document_json = {"elements": [{"id": "title", "type": "title", "x": 1, "y": 1, "w": 90, "h": 10, "text": "第一页"}, {"id": "body", "type": "body", "x": 1, "y": 20, "w": 90, "h": 10, "text": "• A"}]}
        db.commit()
        saved = agent.execute(project["id"], first.id, "updateSlideOutline", {"slide_index": 0, "title": "更新后的第一页", "bullets": ["新的重点"]})
        assert saved["ok"] is True and saved["slide"]["title"] == "更新后的第一页"
        assert saved["slide"]["document"]["elements"][0]["text"] == "更新后的第一页"
        inserted = agent.execute(project["id"], first.id, "saveSlide", {"replace_existing": False, "title": "新增页", "bullets": ["C"], "content": {"elements": []}})
        assert inserted["saved"] is True
        assert service.project(project["id"]).page_count_target == 3
        deleted = agent.execute(project["id"], first.id, "deleteSlide", {"slide_index": 1})
        assert deleted["deleted"] is True
        remaining = sorted(service.project(project["id"]).pages, key=lambda item: item.sort_order)
        assert len(remaining) == 2 and [item.sort_order for item in remaining] == [0, 1]


def test_preview_agent_color_request_updates_page_background_not_section_label():
    with Session() as db:
        user = User(username="color_teacher", email="color@example.test", name="Color", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        service = PptAgentService(db, user)
        project = service.create_project("配色", "制作课件")
        db.add(PptPage(project_id=project["id"], section_title="章节", sort_order=0, title="页面", bullets_json=["要点"], design_document_json={"theme": {"background": "#ffffff"}, "elements": [{"id": "title", "type": "title", "x": 1, "y": 1, "w": 80, "h": 10, "text": "页面", "color": "#173f32"}]})); db.commit()
        page = service.project(project["id"]).pages[0]
        result = PptEditAgent(service).execute(project["id"], page.id, "updateSlideColors", {"slide_index": 0, "background_color": "#f2c94c", "scope": "background"})
        assert result["saved"] is True
        assert result["slide"]["document"]["theme"]["background"] == "#f2c94c"
        assert result["slide"]["document"]["elements"][0]["color"] == "#173f32"


def test_preview_agent_direct_color_request_targets_selected_page():
    with Session() as db:
        user = User(username="color_teacher_2", email="color2@example.test", name="Color", password_hash=hash_password("123456"), role=UserRole.teacher)
        db.add(user); db.commit(); db.refresh(user)
        service = PptAgentService(db, user)
        project = service.create_project("配色", "制作课件")
        db.add_all([PptPage(project_id=project["id"], sort_order=0, title="一", bullets_json=["A"], design_document_json={"elements": []}), PptPage(project_id=project["id"], sort_order=1, title="二", bullets_json=["B"], design_document_json={"elements": []})]); db.commit()
        second = sorted(service.project(project["id"]).pages, key=lambda item: item.sort_order)[1]
        events = list(PptEditAgent(service).run(project["id"], second.id, "这一页的颜色改为黄色"))
        assert events[-1]["chunk"].endswith("#f2c94c。")
        assert service.page(project["id"], second.id).design_document_json["theme"]["background"] == "#f2c94c"
