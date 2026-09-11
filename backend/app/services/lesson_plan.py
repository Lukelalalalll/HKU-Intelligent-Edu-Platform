from pathlib import Path
from sqlalchemy import select
from fastapi import HTTPException
from app.models import LessonPlanProject, LessonPlanPage, LessonPlanAsset, LessonPlanEvent
from app.core.config import settings
from app.services.ppt_agent import encrypt_api_key, decrypt_api_key
from app.services.lesson_plan_graph import LessonPlanWorkflow


def default_document(title=""):
    return {"version": 1, "canvas": {"width": 794, "height": 1123, "unit": "px", "dpi": 96}, "page_size": "A4", "orientation": "portrait", "background": "#ffffff", "elements": ([{"id": "title", "type": "title", "x": 8, "y": 7, "w": 84, "h": 8, "text": title, "font_size": 28, "font_weight": 800, "color": "#075b42"}] if title else [])}


class LessonPlanService:
    def __init__(self, db, user): self.db, self.user = db, user
    def project(self, pid):
        p = self.db.scalar(select(LessonPlanProject).where(LessonPlanProject.id == pid, LessonPlanProject.owner_id == self.user.id))
        if not p: raise HTTPException(404, "学案项目不存在")
        return p
    def serialize(self, p):
        return {"id": p.id, "title": p.title, "request_text": p.request_text, "course_id": p.course_id, "current_stage": p.current_stage, "status": p.status, "page_size": p.page_size, "orientation": p.orientation, "template_id": p.template_id, "page_count": len(p.pages), "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat()}
    def create(self, title, request_text, course_id=None):
        p = LessonPlanProject(owner_id=self.user.id, title=title or "未命名学案", request_text=request_text or "", course_id=course_id); self.db.add(p); self.db.flush(); self.db.add(LessonPlanEvent(project_id=p.id, event_type="project.created", payload_json={})); self.db.commit(); self.db.refresh(p); return self.serialize(p)
    def run(self, pid):
        p = self.project(pid); result = LessonPlanWorkflow().invoke({"project_id": p.id, "request_text": p.request_text, "events": []})
        p.current_stage = "outline"; p.status = "active"
        for i, item in enumerate(result.get("outline", [])):
            page = LessonPlanPage(project_id=p.id, sort_order=i, title=item["title"], page_role=item["role"], document_json=default_document(item["title"]), status="ready"); self.db.add(page)
        for event in result.get("events", []): self.db.add(LessonPlanEvent(project_id=p.id, event_type=event["event_type"], payload_json=event["payload"]))
        self.db.commit(); self.db.refresh(p); return self.serialize(p)
