from .context import *  # noqa: F401,F403
from .mixins_core import _CoreMixin
from .mixins_requirements import _RequirementsMixin
from .mixins_generation import _GenerationMixin
from .mixins_visual import _VisualMixin
from .mixins_document import _DocumentMixin

class PptAgentService(_CoreMixin, _RequirementsMixin, _GenerationMixin, _VisualMixin, _DocumentMixin):
    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user




def _run_visual_research_job(job_id: str, project_id: str, user_id: str) -> None:
    db = SessionLocal()
    try:
        job, project, user = db.get(PptGenerationJob, job_id), db.get(PptProject, project_id), db.get(User, user_id)
        if not job or not project or not user: return
        job.status = "running"; db.commit()
        pages = sorted(project.pages, key=lambda x: x.sort_order)
        def one(page_id: str):
            local = SessionLocal()
            try:
                p, u, page = local.get(PptProject, project_id), local.get(User, user_id), local.get(PptPage, page_id)
                if not p or not u or not page: return False
                svc = PptAgentService(local, u)
                page.statuses_json = {**(page.statuses_json or {}), "visual": "running"}; local.commit()
                svc._event(p, "page.visual.searching", {"job_id": job_id, "page_id": page_id}); local.commit()
                svc._visual_research(p, page); svc._visual_plan(p, page)
                svc._event(p, "page.visual.ready", {"job_id": job_id, "page_id": page_id, "asset_count": len((page.visual_plan_json or {}).get("asset_manifest") or [])}); local.commit()
                return True
            except Exception as exc:
                local.rollback(); page = local.get(PptPage, page_id)
                if page:
                    page.statuses_json = {**(page.statuses_json or {}), "visual": "failed"}
                    page.visual_plan_json = {**(page.visual_plan_json or {}), "asset_status": "failed", "asset_error": str(exc)[:200]}
                    local.commit()
                return False
            finally: local.close()
        # Keep pages in a project serial to reduce search-engine throttling and
        # make completed_pages monotonic for the polling client.
        outcomes = []
        for page in pages:
            ok = one(page.id)
            outcomes.append(ok)
            job = db.get(PptGenerationJob, job_id)
            if job:
                job.completed_pages = sum(1 for item in outcomes if item)
                job.failed_pages = sum(1 for item in outcomes if not item)
                job.current_page_id = page.id
                db.commit()
        job = db.get(PptGenerationJob, job_id)
        job.completed_pages = sum(1 for ok in outcomes if ok); job.failed_pages = sum(1 for ok in outcomes if not ok)
        job.status = "completed" if job.failed_pages == 0 else "completed_with_errors" if job.completed_pages else "failed"; job.finished_at = datetime.now(timezone.utc); db.commit()
    except Exception as exc:
        db.rollback(); job = db.get(PptGenerationJob, job_id)
        if job: job.status, job.error_message = "failed", str(exc)[:500]; job.finished_at = datetime.now(timezone.utc); db.commit()
    finally: db.close()


def _run_generation_job(job_id: str, project_id: str, user_id: str) -> None:
    """Run deck planning and page generation outside the request thread."""
    db = SessionLocal()
    try:
        job = db.get(PptGenerationJob, job_id)
        project = db.get(PptProject, project_id)
        user = db.get(User, user_id)
        if not job or not project or not user or job.status == "cancelled":
            return
        service = PptAgentService(db, user)
        job.status, job.stage, job.started_at = "running", "planning", datetime.now(timezone.utc)
        service._event(project, "generation.started", {"job_id": job.id, "total_pages": job.total_pages}); db.commit()
        pages = sorted(project.pages, key=lambda x: x.sort_order)
        outline = [{"id": p.id, "order": p.sort_order, "section": p.section_title, "title": p.title, "bullets": p.bullets_json or []} for p in pages]
        source_context = service._source_context(project)
        planner_prompt = """你是教学课件 Deck Planner。只输出 JSON：{pages:[{id,role,core_message,content_requirements,visual_type,speaker_notes}]}。大纲只是教学主线，不是页面全文。必须为页面分配 cover、catalogue、section、concept、comparison、process、case、quote、summary、cta 等角色；第一页必须 cover，第二页必须 catalogue。根据主题与页面上下文补充论点、案例、数据和视觉表达建议，不能编造引用。"""
        try:
            planner = ProviderGateway(db, user.id).json(planner_prompt, {"request": project.request_text, "outline": outline, "requirements": source_context})
        except Exception:
            planner = {"pages": []}
        plan_by_id = {str(item.get("id")): item for item in (planner.get("pages") or []) if isinstance(item, dict) and item.get("id")}
        roles = ["cover", "catalogue"]
        for index, page in enumerate(pages):
            item = plan_by_id.get(page.id, {})
            role = str(item.get("role") or (roles[index] if index < 2 else "concept"))
            page.page_role = role
            page.content_plan_json = item
            page.visual_plan_json = {"type": item.get("visual_type") or role}
        job.planner_json = planner if isinstance(planner, dict) else {}; job.stage = "content"; db.commit()
        service._event(project, "planner.completed", {"job_id": job.id}); db.commit()

        layouts = {item["id"]: item for item in __import__("app.services.ppt_theme", fromlist=["list_layouts"]).list_layouts(project.theme_id or "light-academic")}
        layout_list = list(layouts.values())
        assignments = {}
        for index, page in enumerate(pages):
            role = page.page_role
            preferred = "section" if role == "section" else "quote" if role in {"quote", "summary"} else "two-column" if role in {"comparison", "process", "case"} else "title-content"
            assignments[page.id] = next((x["id"] for x in layout_list if x["kind"] in {preferred, "content"} or x["id"] == preferred), layout_list[0]["id"])
        project.layout_assignments = assignments; project.current_stage = "design"; db.commit()

        def render_one(page_id: str):
            local = SessionLocal()
            try:
                p = local.get(PptProject, project_id); u = local.get(User, user_id); page = local.get(PptPage, page_id)
                if not p or not u or not page: return False
                svc = PptAgentService(local, u)
                svc._event(p, "page.content_started", {"job_id": job_id, "page_id": page_id}); local.commit()
                try:
                    svc._visual_research(p, page)
                    svc._visual_plan(p, page)
                    svc._event(p, "page.visual_research_completed", {"job_id": job_id, "page_id": page_id, "asset_count": len((page.visual_plan_json or {}).get("asset_manifest") or [])})
                    local.commit()
                except Exception as exc:
                    # Visual enrichment is best-effort; text-only generation must
                    # remain available when search/image providers are down.
                    page.visual_plan_json = {**(page.visual_plan_json or {}), "asset_status": "degraded", "asset_error": str(exc)[:200]}
                    page.statuses_json = {**(page.statuses_json or {}), "visual": "failed"}
                    local.commit()
                try:
                    combined = ProviderGateway(local, u.id).json("只输出 JSON：{bullets:[string],summary:string,speaker_notes:string,citations:[object],visual_plan:object,elements:[{type,x,y,w,h,text,items,src,font_size,font_weight,color,fill}]}. 根据页面主线与资料补充教学内容并设计版式；不编造引用，坐标使用 0-100 百分比，标题 30-44px、正文 18-24px，避免重叠和文字堆叠。", {"project": p.request_text, "page": svc.serialize_page(page), "plan": page.content_plan_json or {}, "sources": source_context, "layout": layouts.get(assignments.get(page_id), layout_list[0]), "theme": p.theme_config or {}})
                    if isinstance(combined, dict):
                        if isinstance(combined.get("bullets"), list) and combined["bullets"]: page.bullets_json = [str(x) for x in combined["bullets"][:8]]
                        page.summary_md = str(combined.get("summary") or page.summary_md or "")
                        page.speaker_notes = str(combined.get("speaker_notes") or page.speaker_notes or "")
                        if isinstance(combined.get("citations"), list): page.citations_json = combined["citations"][:30]
                        page.visual_plan_json = combined.get("visual_plan") if isinstance(combined.get("visual_plan"), dict) else page.visual_plan_json
                        document = svc._apply_visual_plan(page, svc._normalize_document(combined, layouts.get(assignments.get(page_id), layout_list[0]), p.theme_config or {}))
                    else:
                        raise ValueError("invalid combined design")
                except Exception:
                    try:
                        document = svc._slide_doc(p, page, "design", layout=layouts.get(assignments.get(page_id), layout_list[0]), outline=outline)
                    except Exception:
                        document = svc._template_document(page, p.theme_config or {}, layouts.get(assignments.get(page_id), layout_list[0]))
                svc._event(p, "page.content_completed", {"job_id": job_id, "page_id": page_id}); local.commit()
                layout = layouts.get(assignments.get(page_id), layout_list[0])
                if not svc._document_quality_ok(document):
                    try:
                        repaired = svc._slide_doc(p, page, "design_repair", layout=layout, outline=outline)
                        document = repaired if svc._document_quality_ok(repaired) else svc._template_document(page, p.theme_config or {}, layout)
                    except Exception:
                        document = svc._template_document(page, p.theme_config or {}, layout)
                page.design_document_json = document; page.document_revision += 1; page.statuses_json = {**(page.statuses_json or {}), "design": "ready"}
                version_no = (local.scalar(select(PptDocumentVersion).where(PptDocumentVersion.page_id == page.id).order_by(PptDocumentVersion.version_no.desc())) or PptDocumentVersion(version_no=0)).version_no + 1
                version = PptDocumentVersion(project_id=p.id, page_id=page.id, version_no=version_no, document_json=document)
                local.add(version); local.flush(); page.current_document_version_id = version.id
                local.commit()
                progress = local.scalar(select(PptGenerationJob).where(PptGenerationJob.id == job_id).with_for_update())
                if progress:
                    progress.completed_pages = min(progress.total_pages, (progress.completed_pages or 0) + 1)
                    progress.current_page_id = page_id
                    completed = progress.completed_pages
                    total = progress.total_pages
                else:
                    completed = 0
                    total = len(p.pages)
                svc._event(p, "page.designed", {"job_id": job_id, "page_id": page_id, "layout_id": layout["id"], "completed_pages": completed, "total_pages": total}); local.commit()
                return True
            finally:
                local.close()

        results = [render_one(page_id) for page_id in [p.id for p in pages]]
        job = db.get(PptGenerationJob, job_id)
        job.completed_pages = sum(1 for ok in results if ok); job.failed_pages = len(results) - job.completed_pages; job.stage = "quality"; db.commit()
        service._event(project, "generation.quality_checked", {"job_id": job.id, "completed_pages": job.completed_pages, "failed_pages": job.failed_pages});
        job.status = "completed" if not job.failed_pages else "completed_with_errors"; job.stage = "completed"; job.finished_at = datetime.now(timezone.utc); project.design_status = "ready"; project.current_stage = "design"; db.commit()
        service._event(project, "generation.completed", {"job_id": job.id, "completed_pages": job.completed_pages, "failed_pages": job.failed_pages}); db.commit()
    except Exception as exc:
        db.rollback(); job = db.get(PptGenerationJob, job_id)
        if job:
            job.status, job.stage, job.error_message = "failed", "failed", str(exc); job.finished_at = datetime.now(timezone.utc); db.commit()
            project = db.get(PptProject, project_id)
            if project:
                PptAgentService(db, db.get(User, user_id))._event(project, "generation.failed", {"job_id": job_id, "error": str(exc)}); db.commit()
    finally:
        db.close()




