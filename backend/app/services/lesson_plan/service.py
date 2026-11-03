"""Lesson plan application service.

The service owns the full teacher workflow: project lifecycle, material
uploads, the requirement interview (streaming and non-streaming), generation
and rewriting of Markdown pages, and PDF/Markdown export.  Route handlers stay
thin; every state transition lives here.
"""

from __future__ import annotations

import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    LessonPlanExportJob,
    LessonPlanMessage,
    LessonPlanPage,
    LessonPlanProject,
    User,
)
from app.services.ai_gateway import AIGateway
from app.services.provider_contract import ProviderError

from . import prompts
from .export import ExportRenderError, render_pdf
from .files import (
    asset_by_id,
    assets_for_project,
    context_materials,
    delete_asset,
    project_root,
    serialize_asset,
    store_upload,
)
from .markdown import build_export_html, build_markdown_export
from .normalize import (
    coerce_include_answers,
    coerce_page_count,
    document_markdown,
    normalize_document,
    normalize_interview,
    normalize_page,
    normalize_page_updates,
    normalize_plan,
    slug_filename,
)

# One in-process lock per project keeps double-clicks from starting two
# generations.  This is a best-effort guard for a single API process; the
# database row remains the source of truth for the produced pages.
_GENERATION_LOCKS: dict[str, threading.Lock] = {}
_GENERATION_LOCKS_GUARD = threading.Lock()

MAX_HISTORY_MESSAGES = 24
MAX_MESSAGE_CHARS = 8000
MAX_MATERIAL_REFERENCES = 6


def _lock_for(project_id: str) -> threading.Lock:
    """Return the generation lock for one project."""
    with _GENERATION_LOCKS_GUARD:
        lock = _GENERATION_LOCKS.get(project_id)
        if lock is None:
            lock = threading.Lock()
            _GENERATION_LOCKS[project_id] = lock
        return lock


class LessonPlanService:
    """Application service bound to one teacher session."""

    def __init__(self, db: Session, user: User):
        """Store the request session and the authenticated teacher."""
        self.db = db
        self.user = user

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def project(self, project_id: str) -> LessonPlanProject:
        """Load a project owned by the caller.

        Raises:
            HTTPException: 404 when the project does not exist for this teacher.
        """
        project = self.db.scalar(
            select(LessonPlanProject).where(
                LessonPlanProject.id == project_id,
                LessonPlanProject.owner_id == self.user.id,
            )
        )
        if not project:
            raise HTTPException(404, "学案项目不存在")
        return project

    def serialize(self, project: LessonPlanProject, page_count: int | None = None) -> dict[str, Any]:
        """Serialize one project summary."""
        settings_data = self._settings(project)
        return {
            "id": project.id,
            "title": project.title,
            "request_text": project.request_text,
            "course_id": project.course_id,
            "current_stage": project.current_stage,
            "status": project.status,
            "page_size": project.page_size,
            "orientation": project.orientation,
            "template_id": project.template_id,
            "page_count": page_count if page_count is not None else len(self._pages(project.id)),
            "brief_summary": settings_data.get("brief_summary") or "",
            "ready_to_generate": bool(settings_data.get("ready")),
            "degraded": bool(settings_data.get("degraded")),
            "degraded_reason": settings_data.get("degraded_reason") or "",
            "suggested_additions": list(settings_data.get("suggested_additions") or []),
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

    def list_projects(self) -> list[dict[str, Any]]:
        """List the caller's projects, most recently updated first."""
        rows = self.db.scalars(
            select(LessonPlanProject)
            .where(LessonPlanProject.owner_id == self.user.id)
            .order_by(LessonPlanProject.updated_at.desc())
            .limit(60)
        ).all()
        counts = {
            project_id: count
            for project_id, count in self.db.execute(
                select(LessonPlanPage.project_id, _count_pages()).group_by(LessonPlanPage.project_id)
            ).all()
        }
        return [self.serialize(row, page_count=counts.get(row.id, 0)) for row in rows]

    def create(self, title: str = "", request_text: str = "", course_id: str | None = None) -> dict[str, Any]:
        """Create an empty project and record its creation event."""
        text = (request_text or "").strip()
        resolved_title = (title or "").strip() or (text.splitlines()[0][:40] if text else "未命名学案")
        project = LessonPlanProject(
            owner_id=self.user.id,
            title=resolved_title[:200],
            request_text=text[:20000],
            course_id=course_id or None,
            current_stage="init",
            settings_json={
                "answers": {},
                "brief_summary": "",
                "ready": False,
                "suggested_additions": [],
                "auto_title": not bool((title or "").strip()),
                "degraded": False,
                "degraded_reason": "",
            },
        )
        self.db.add(project)
        self.db.flush()
        self._event(project, "project.created", {"title": project.title})
        self.db.commit()
        self.db.refresh(project)
        return self.serialize(project)

    def delete(self, project_id: str) -> dict[str, bool]:
        """Delete a project and its export artifacts."""
        project = self.project(project_id)
        shutil.rmtree(project_root(project.id), ignore_errors=True)
        self.db.delete(project)
        self.db.commit()
        return {"ok": True}

    def capabilities(self) -> dict[str, Any]:
        """Report whether the lesson-plan business has a usable model."""
        try:
            health = AIGateway(self.db, prompts.BUSINESS_CODE).health_check()
        except Exception:
            return {"ai_configured": False, "model": None}
        configured = health.get("status") == "configured"
        return {"ai_configured": configured, "model": health.get("model") if configured else None}

    # ------------------------------------------------------------------
    # Workspace state
    # ------------------------------------------------------------------
    def state(self, project_id: str) -> dict[str, Any]:
        """Return everything the workspace needs in one request."""
        project = self.project(project_id)
        settings_data = self._settings(project)
        pages = self._pages(project.id)
        assets = assets_for_project(self.db, project.id)
        latest_export = self.db.scalar(
            select(LessonPlanExportJob)
            .where(LessonPlanExportJob.project_id == project.id)
            .order_by(LessonPlanExportJob.created_at.desc())
        )
        return {
            "project": self.serialize(project, page_count=len(pages)),
            "pages": [self.serialize_page(page) for page in pages],
            "messages": [self.serialize_message(message) for message in self._recent_messages(project.id, limit=40)],
            "answers": settings_data.get("answers") or {},
            "brief_summary": settings_data.get("brief_summary") or "",
            "ready_to_generate": bool(settings_data.get("ready")),
            "suggested_additions": list(settings_data.get("suggested_additions") or []),
            "degraded": bool(settings_data.get("degraded")),
            "degraded_reason": settings_data.get("degraded_reason") or "",
            "assets": [serialize_asset(asset) for asset in assets],
            "capabilities": self.capabilities(),
            "latest_export": self.serialize_export(latest_export) if latest_export else None,
        }

    # ------------------------------------------------------------------
    # Materials
    # ------------------------------------------------------------------
    def add_file(self, project_id: str, upload) -> dict[str, Any]:
        """Store one uploaded material and return its summary."""
        project = self.project(project_id)
        asset = store_upload(self.db, self.user, project, upload)
        self._event(project, "file.uploaded", {"asset_id": asset.id, "title": asset.title})
        self.db.commit()
        return serialize_asset(asset)

    def delete_file(self, project_id: str, asset_id: str) -> dict[str, bool]:
        """Remove one material reference from the project."""
        project = self.project(project_id)
        asset = asset_by_id(self.db, project.id, asset_id)
        delete_asset(self.db, asset)
        self._event(project, "file.removed", {"asset_id": asset_id})
        self.db.commit()
        return {"ok": True}

    def asset_path(self, project_id: str, asset_id: str) -> Path:
        """Resolve an uploaded material for download.

        Raises:
            HTTPException: 404 when the row or the file is missing.
        """
        project = self.project(project_id)
        asset = asset_by_id(self.db, project.id, asset_id)
        path = Path(asset.file_path or "")
        if not path.is_file():
            raise HTTPException(404, "资料文件不存在")
        return path

    def list_pages(self, project_id: str) -> list[dict[str, Any]]:
        """Return the serialized pages of a project in display order."""
        project = self.project(project_id)
        return [self.serialize_page(page) for page in self._pages(project.id)]

    # ------------------------------------------------------------------
    # Interview
    # ------------------------------------------------------------------
    def interview(self, project_id: str, content: str | None = None, bootstrap: bool = False, option_label: str | None = None) -> dict[str, Any]:
        """Run one non-streaming interview/refinement turn."""
        project, text, answers, materials, history, mode, system_prompt, payload = self._prepare_chat(project_id, content, bootstrap, option_label)
        degraded, reason = False, ""
        try:
            data = self._gateway().json(system_prompt, payload)
        except (HTTPException, ProviderError) as exc:
            degraded, reason = True, self._error_detail(exc)
            data = self._fallback_chat_data(mode, answers, reason)
        except Exception as exc:  # noqa: BLE001 - third-party SDKs raise broadly
            degraded, reason = True, str(exc)[:300]
            data = self._fallback_chat_data(mode, answers, reason)
        return self._apply_chat(project, mode, data, degraded=degraded, reason=reason, user_text=text)

    def interview_stream(self, project_id: str, content: str | None = None, bootstrap: bool = False, option_label: str | None = None) -> Iterator[dict[str, Any]]:
        """Yield chat chunks and always terminate with a ``complete`` event."""
        project, text, answers, materials, history, mode, system_prompt, payload = self._prepare_chat(project_id, content, bootstrap, option_label)
        completed = False
        try:
            for event in self._gateway().stream_json(system_prompt, payload):
                if event.get("type") == "chunk":
                    yield event
                elif event.get("type") == "final":
                    completed = True
                    yield {
                        "type": "complete",
                        "result": self._apply_chat(project, mode, event.get("data") or {}, degraded=False, reason="", user_text=text),
                    }
        except (HTTPException, ProviderError) as exc:
            reason = self._error_detail(exc)
        except Exception as exc:  # noqa: BLE001 - third-party SDKs raise broadly
            reason = str(exc)[:300]
        if completed:
            return
        data = self._fallback_chat_data(mode, answers, reason)
        yield {
            "type": "complete",
            "result": self._apply_chat(project, mode, data, degraded=True, reason=reason, user_text=text),
        }

    def _prepare_chat(self, project_id: str, content: str | None, bootstrap: bool, option_label: str | None):
        """Append the user turn and assemble the model payload."""
        project = self.project(project_id)
        text = (option_label or content or "").strip()
        if not bootstrap and not text:
            raise HTTPException(400, "请输入内容")
        if text and not bootstrap:
            self._message(project, "user", text[:MAX_MESSAGE_CHARS])
            self.db.commit()
        answers = self._answers(project)
        materials = context_materials(self.db, project)
        history = [
            {"role": message.role, "content": message.content_md}
            for message in self._recent_messages(project.id, limit=MAX_HISTORY_MESSAGES)
        ]
        pages = self._pages(project.id)
        if pages and not bootstrap:
            mode = "refine"
            system_prompt = prompts.REFINE_SYSTEM
            payload = {
                "request": project.request_text,
                "answers": answers,
                "history": history,
                "materials": [{"title": item["title"], "excerpt": item["text"][:2000]} for item in materials],
                "pages": [
                    {
                        "page_id": page.id,
                        "title": page.title,
                        "page_role": page.page_role,
                        "markdown": document_markdown(page.document_json)[:4000],
                    }
                    for page in pages[:MAX_MATERIAL_REFERENCES]
                ],
                "message": text,
            }
        else:
            mode = "interview"
            system_prompt = prompts.INTERVIEW_SYSTEM
            payload = {
                "request": project.request_text,
                "answers": answers,
                "history": history,
                "materials": [{"title": item["title"], "excerpt": item["text"][:3000]} for item in materials],
                "bootstrap": bootstrap,
            }
        return project, text, answers, materials, history, mode, system_prompt, payload

    def _fallback_chat_data(self, mode: str, answers: dict[str, Any], reason: str) -> dict[str, Any]:
        """Return deterministic chat data for the current mode."""
        if mode == "refine":
            return {
                "assistant_markdown": "（当前无法调用 AI 模型，修改意见已记录。请先在管理员处配置模型，或直接在预览里编辑页面。）",
                "page_updates": [],
                "needs_regenerate": False,
                "__fallback_reason": reason,
            }
        return prompts.interview_fallback(answers, reason)

    def _apply_chat(self, project: LessonPlanProject, mode: str, data: dict[str, Any], *, degraded: bool, reason: str, user_text: str = "") -> dict[str, Any]:
        """Persist one assistant turn and return the SSE/HTTP payload."""
        if mode == "refine":
            return self._apply_refine(project, data, degraded=degraded, reason=reason)
        normalized = normalize_interview(data)
        settings_data = self._settings(project)
        answers = dict(settings_data.get("answers") or {})
        answers.update(normalized["answers_patch"])
        asked_code = normalized.get("__asked_code")
        if asked_code:
            asked = [str(item) for item in answers.get("__asked") or []]
            if asked_code not in asked:
                asked.append(asked_code)
            answers["__asked"] = asked
        if degraded and user_text:
            previous = str(answers.get("notes") or "").strip()
            merged = (previous + "\n" + user_text).strip()
            answers["notes"] = merged[-2000:]
        ready = bool(normalized["ready_to_generate"])
        brief = normalized["brief_summary"] or settings_data.get("brief_summary") or prompts.brief_summary(answers)
        message = self._message(
            project,
            "assistant",
            normalized["assistant_markdown"],
            {
                "question": normalized["question"],
                "ready_to_generate": ready,
                "degraded": degraded,
                "suggested_additions": normalized["suggested_additions"],
            },
        )
        settings_data.update(
            {
                "answers": answers,
                "brief_summary": brief,
                "ready": ready,
                "suggested_additions": normalized["suggested_additions"],
                "degraded": degraded,
                "degraded_reason": reason,
            }
        )
        self._store_settings(project, settings_data)
        if project.current_stage in {"init", "collecting", "ready"}:
            project.current_stage = "ready" if ready else "collecting"
        self._event(project, "requirement.updated", {"ready": ready, "degraded": degraded})
        self.db.commit()
        return {
            "message": self.serialize_message(message),
            "question": normalized["question"],
            "answers": answers,
            "brief_summary": brief,
            "ready_to_generate": ready,
            "suggested_additions": normalized["suggested_additions"],
            "degraded": degraded,
            "degraded_reason": reason,
            "mode": "interview",
        }

    def _apply_refine(self, project: LessonPlanProject, data: dict[str, Any], *, degraded: bool, reason: str) -> dict[str, Any]:
        """Persist refinement updates returned by the model."""
        payload = data if isinstance(data, dict) else {}
        updates = normalize_page_updates(payload, {page.id for page in self._pages(project.id)})
        for update in updates:
            page = self._page(project.id, update["page_id"])
            page.document_json = {"version": 2, "markdown": update["markdown"]}
            page.status = "edited"
            page.revision += 1
        reply = str(payload.get("assistant_markdown") or "").strip()[:6000]
        if not reply:
            reply = "已记录修改意见。" if not updates else f"已更新 {len(updates)} 页。"
        message = self._message(
            project,
            "assistant",
            reply,
            {
                "page_updates": [update["page_id"] for update in updates],
                "needs_regenerate": bool(payload.get("needs_regenerate")),
                "degraded": degraded,
            },
        )
        settings_data = self._settings(project)
        settings_data["degraded"] = degraded
        settings_data["degraded_reason"] = reason
        self._store_settings(project, settings_data)
        if updates:
            self._event(project, "pages.refined", {"page_ids": [update["page_id"] for update in updates]})
        self.db.commit()
        return {
            "message": self.serialize_message(message),
            "question": None,
            "answers": self._answers(project),
            "brief_summary": settings_data.get("brief_summary") or "",
            "ready_to_generate": bool(settings_data.get("ready")),
            "suggested_additions": list(settings_data.get("suggested_additions") or []),
            "page_updates": [update["page_id"] for update in updates],
            "needs_regenerate": bool(payload.get("needs_regenerate")),
            "degraded": degraded,
            "degraded_reason": reason,
            "mode": "refine",
        }

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def generate(self, project_id: str, page_count: int | None = None, include_answers: bool | None = None, instruction: str | None = None) -> dict[str, Any]:
        """Generate a lesson plan, replacing any previous pages."""
        project = self.project(project_id)
        lock = _lock_for(project.id)
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "正在生成学案，请稍候")
        try:
            answers = self._answers(project)
            materials = context_materials(self.db, project)
            if not project.request_text.strip() and not materials and not answers.get("objectives"):
                raise HTTPException(400, "请先描述学案需求或上传资料")
            target_pages = coerce_page_count(page_count if page_count is not None else answers.get("page_count"))
            answers_visible = coerce_include_answers(
                include_answers if include_answers is not None else answers.get("include_answers")
            )
            payload = {
                "request": project.request_text,
                "answers": answers,
                "materials": [{"title": item["title"], "excerpt": item["text"][:3000]} for item in materials],
                "page_count": target_pages,
                "include_answers": answers_visible,
                "instruction": (instruction or "").strip()[:2000],
            }
            degraded, reason = False, ""
            try:
                data = self._gateway().json(prompts.generation_system(target_pages, answers_visible), payload)
                plan = normalize_plan(data, page_count=target_pages, include_answers=answers_visible)
            except (HTTPException, ProviderError) as exc:
                degraded, reason = True, self._error_detail(exc)
                plan = self._template_plan(project, answers, materials, target_pages, answers_visible)
            except Exception as exc:  # noqa: BLE001 - third-party SDKs raise broadly
                degraded, reason = True, str(exc)[:300]
                plan = self._template_plan(project, answers, materials, target_pages, answers_visible)
            return self._persist_plan(project, plan, answers, target_pages, answers_visible, degraded, reason)
        finally:
            lock.release()

    def _template_plan(self, project: LessonPlanProject, answers: dict[str, Any], materials: list[dict[str, Any]], page_count: int, include_answers: bool) -> dict[str, Any]:
        """Build and validate the deterministic fallback plan."""
        raw = prompts.template_plan(
            title=project.title,
            request_text=project.request_text,
            answers=answers,
            materials=materials,
            page_count=page_count,
            include_answers=include_answers,
        )
        return normalize_plan(raw, page_count=page_count, include_answers=include_answers)

    def _persist_plan(self, project: LessonPlanProject, plan: dict[str, Any], answers: dict[str, Any], page_count: int, include_answers: bool, degraded: bool, reason: str) -> dict[str, Any]:
        """Replace project pages with the generated plan and persist metadata."""
        self.db.execute(delete(LessonPlanPage).where(LessonPlanPage.project_id == project.id))
        self.db.flush()
        for index, item in enumerate(plan["pages"]):
            self.db.add(
                LessonPlanPage(
                    project_id=project.id,
                    sort_order=index,
                    title=item["title"],
                    page_role=item["page_role"],
                    document_json={"version": 2, "markdown": item["markdown"]},
                    status="draft" if degraded else "ready",
                )
            )
        settings_data = self._settings(project)
        auto_title = bool(settings_data.get("auto_title"))
        if auto_title and plan.get("title"):
            project.title = str(plan["title"])[:200]
            settings_data["auto_title"] = False
        merged_answers = {**answers}
        if plan.get("subject"):
            merged_answers["subject"] = plan["subject"]
        if plan.get("grade"):
            merged_answers["grade"] = plan["grade"]
        if plan.get("duration_minutes"):
            merged_answers["duration_minutes"] = plan["duration_minutes"]
        merged_answers["page_count"] = page_count
        merged_answers["include_answers"] = include_answers
        summary = str(plan.get("summary_markdown") or "").strip()
        if summary:
            self._message(
                project,
                "assistant",
                summary,
                {"intent_type": "plan_generated", "pages": len(plan["pages"]), "degraded": degraded},
            )
        settings_data.update(
            {
                "answers": merged_answers,
                "ready": True,
                "degraded": degraded,
                "degraded_reason": reason,
            }
        )
        if not settings_data.get("brief_summary"):
            settings_data["brief_summary"] = prompts.brief_summary(merged_answers)
        self._store_settings(project, settings_data)
        project.current_stage = "outline"
        self._event(
            project,
            "pages.generated",
            {"pages": len(plan["pages"]), "degraded": degraded, "reason": reason},
        )
        self.db.commit()
        pages = self._pages(project.id)
        return {
            "project": self.serialize(project, page_count=len(pages)),
            "pages": [self.serialize_page(page) for page in pages],
            "summary_markdown": summary,
            "degraded": degraded,
            "degraded_reason": reason,
        }

    def regenerate_page(self, project_id: str, page_id: str, instruction: str | None = None) -> dict[str, Any]:
        """Rewrite one page, keeping the original on provider failure."""
        project = self.project(project_id)
        page = self._page(project.id, page_id)
        answers = self._answers(project)
        materials = context_materials(self.db, project)
        payload = {
            "request": project.request_text,
            "answers": answers,
            "materials": [{"title": item["title"], "excerpt": item["text"][:2000]} for item in materials],
            "page": {
                "title": page.title,
                "page_role": page.page_role,
                "markdown": document_markdown(page.document_json)[:8000],
            },
            "instruction": (instruction or "").strip()[:2000],
        }
        degraded, reason = False, ""
        try:
            data = self._gateway().json(prompts.PAGE_REWRITE_SYSTEM, payload)
            normalized = normalize_page(data)
            page.title = normalized["title"]
            page.page_role = normalized["page_role"]
            page.document_json = {"version": 2, "markdown": normalized["markdown"]}
            page.status = "ready"
            page.revision += 1
            self._event(project, "page.regenerated", {"page_id": page.id})
        except (HTTPException, ProviderError) as exc:
            degraded, reason = True, self._error_detail(exc)
        except Exception as exc:  # noqa: BLE001 - third-party SDKs raise broadly
            degraded, reason = True, str(exc)[:300]
        settings_data = self._settings(project)
        settings_data["degraded"] = degraded
        settings_data["degraded_reason"] = reason
        self._store_settings(project, settings_data)
        self.db.commit()
        return {
            "page": self.serialize_page(page),
            "degraded": degraded,
            "degraded_reason": reason,
        }

    def patch_page(self, project_id: str, page_id: str, document: dict[str, Any], revision: int) -> dict[str, Any]:
        """Save teacher edits with optimistic concurrency.

        Raises:
            HTTPException: 409 when the page was edited elsewhere.
        """
        project = self.project(project_id)
        page = self._page(project.id, page_id)
        if int(revision) != page.revision:
            raise HTTPException(409, "页面已被更新，请刷新后重试")
        try:
            normalized = normalize_document(document)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        page.document_json = normalized
        page.status = "edited"
        page.revision += 1
        self._event(project, "page.updated", {"page_id": page.id})
        self.db.commit()
        self.db.refresh(page)
        return self.serialize_page(page)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_pdf(self, project_id: str, include_answers: bool = True, black_white: bool = False) -> dict[str, Any]:
        """Render the plan to PDF and record the export job."""
        project = self.project(project_id)
        pages = self._pages(project.id)
        if not pages:
            raise HTTPException(409, "请先生成学案")
        root = project_root(project.id)
        root.mkdir(parents=True, exist_ok=True)
        job = LessonPlanExportJob(project_id=project.id, status="running")
        self.db.add(job)
        self.db.flush()
        html_path = root / f"lesson-plan-{job.id}.html"
        pdf_path = root / f"lesson-plan-{job.id}.pdf"
        html_text = build_export_html(self._project_meta(project), [self.serialize_page(page) for page in pages], include_answers, black_white)
        html_path.write_text(html_text, encoding="utf-8")
        try:
            render_pdf(html_text, pdf_path)
            job.status = "completed"
            job.pdf_path = str(pdf_path)
            job.html_path = str(html_path)
            if project.current_stage == "outline":
                project.current_stage = "exported"
            self._event(project, "export.completed", {"job_id": job.id, "include_answers": include_answers})
            self.db.commit()
        except ExportRenderError as exc:
            job.status = "failed"
            job.error_message = str(exc)[:4000]
            job.html_path = str(html_path)
            self._event(project, "export.failed", {"job_id": job.id, "error": job.error_message})
            self.db.commit()
        return self.serialize_export(job)

    def export_markdown(self, project_id: str, include_answers: bool = True) -> tuple[str, bytes]:
        """Build the downloadable Markdown lesson plan."""
        project = self.project(project_id)
        pages = self._pages(project.id)
        if not pages:
            raise HTTPException(409, "请先生成学案")
        content = build_markdown_export(
            self._project_meta(project),
            [self.serialize_page(page) for page in pages],
            include_answers,
        )
        if project.current_stage == "outline":
            project.current_stage = "exported"
            self._event(project, "export.completed", {"format": "markdown", "include_answers": include_answers})
            self.db.commit()
        stamp = datetime.now().strftime("%Y%m%d")
        filename = f"{slug_filename(project.title, 'lesson-plan')}-{stamp}.md"
        return filename, content.encode("utf-8")

    def export_job(self, project_id: str, export_id: str) -> LessonPlanExportJob:
        """Load one export job scoped to the project.

        Raises:
            HTTPException: 404 when the job is unknown.
        """
        project = self.project(project_id)
        job = self.db.scalar(
            select(LessonPlanExportJob).where(
                LessonPlanExportJob.id == export_id,
                LessonPlanExportJob.project_id == project.id,
            )
        )
        if not job:
            raise HTTPException(404, "导出任务不存在")
        return job

    def export_path(self, project_id: str, export_id: str) -> Path:
        """Resolve the PDF of a completed export.

        Raises:
            HTTPException: 409 when the export is unfinished, 404 when the file
                is missing.
        """
        job = self.export_job(project_id, export_id)
        if job.status != "completed":
            raise HTTPException(409, "导出尚未完成")
        path = Path(job.pdf_path or "")
        if not path.is_file():
            raise HTTPException(404, "导出文件不存在")
        return path

    def serialize_export(self, job: LessonPlanExportJob) -> dict[str, Any]:
        """Serialize one export job."""
        return {
            "id": job.id,
            "status": job.status,
            "error": job.error_message or "",
            "created_at": job.created_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _gateway(self) -> AIGateway:
        """Return the gateway for the lesson-plan business."""
        return AIGateway(self.db, prompts.BUSINESS_CODE)

    @staticmethod
    def _error_detail(exc: Exception) -> str:
        """Return a short, teacher-safe provider error message."""
        if isinstance(exc, HTTPException):
            return str(exc.detail)
        return str(exc)[:300] or "AI 模型调用失败"

    def _settings(self, project: LessonPlanProject) -> dict[str, Any]:
        """Return a mutable copy of the project settings bag."""
        return dict(project.settings_json or {})

    def _store_settings(self, project: LessonPlanProject, settings_data: dict[str, Any]) -> None:
        """Replace the settings bag so SQLAlchemy detects the change."""
        project.settings_json = dict(settings_data)

    def _answers(self, project: LessonPlanProject) -> dict[str, Any]:
        """Return a copy of the collected interview answers."""
        return dict(self._settings(project).get("answers") or {})

    def _project_meta(self, project: LessonPlanProject) -> dict[str, Any]:
        """Return the fields used by the PDF/Markdown renderers."""
        answers = self._answers(project)
        return {
            "title": project.title,
            "subject": answers.get("subject") or "",
            "grade": answers.get("grade") or "",
            "duration_minutes": answers.get("duration_minutes") or "",
        }

    def _pages(self, project_id: str) -> list[LessonPlanPage]:
        """Return the project pages in display order."""
        return list(
            self.db.scalars(
                select(LessonPlanPage)
                .where(LessonPlanPage.project_id == project_id)
                .order_by(LessonPlanPage.sort_order.asc(), LessonPlanPage.id.asc())
            )
        )

    def _page(self, project_id: str, page_id: str) -> LessonPlanPage:
        """Load one page scoped to its project.

        Raises:
            HTTPException: 404 when the page is unknown.
        """
        page = self.db.scalar(
            select(LessonPlanPage).where(
                LessonPlanPage.id == page_id,
                LessonPlanPage.project_id == project_id,
            )
        )
        if not page:
            raise HTTPException(404, "页面不存在")
        return page

    def _recent_messages(self, project_id: str, limit: int = 24) -> list[LessonPlanMessage]:
        """Return the most recent messages in chronological order."""
        rows = list(
            self.db.scalars(
                select(LessonPlanMessage)
                .where(LessonPlanMessage.project_id == project_id)
                .order_by(LessonPlanMessage.created_at.desc(), LessonPlanMessage.id.desc())
                .limit(limit)
            )
        )
        return list(reversed(rows))

    def _message(self, project: LessonPlanProject, role: str, content: str, payload: dict[str, Any] | None = None) -> LessonPlanMessage:
        """Persist one chat message."""
        message = LessonPlanMessage(
            project_id=project.id,
            role=role,
            content_md=(content or "")[:MAX_MESSAGE_CHARS],
            payload_json=payload or {},
        )
        self.db.add(message)
        self.db.flush()
        return message

    def _event(self, project: LessonPlanProject, event_type: str, payload: dict[str, Any]) -> None:
        """Append one project event."""
        from app.models import LessonPlanEvent

        self.db.add(LessonPlanEvent(project_id=project.id, event_type=event_type, payload_json=payload))

    def serialize_page(self, page: LessonPlanPage) -> dict[str, Any]:
        """Serialize one page document."""
        return {
            "id": page.id,
            "title": page.title,
            "page_role": page.page_role,
            "sort_order": page.sort_order,
            "document": page.document_json or {},
            "markdown": document_markdown(page.document_json),
            "revision": page.revision,
            "status": page.status,
        }

    def serialize_message(self, message: LessonPlanMessage) -> dict[str, Any]:
        """Serialize one chat message."""
        return {
            "id": message.id,
            "role": message.role,
            "content_md": message.content_md,
            "payload": message.payload_json or {},
            "created_at": message.created_at.isoformat(),
        }


def _count_pages():
    """Return the ``count(*)`` expression used by the project list."""
    from sqlalchemy import func

    return func.count(LessonPlanPage.id)


__all__ = ["LessonPlanService"]
