from .context import *  # noqa: F401,F403

class _GenerationMixin:
    def start_generation(self, project_id: str) -> dict[str, Any]:
        p = self.project(project_id)
        if not p.theme_id:
            raise HTTPException(409, "请先选择主题")
        with _GENERATION_LOCKS_GUARD:
            lock = _GENERATION_LOCKS.setdefault(p.id, threading.Lock())
        with lock:
            existing = self.db.scalar(select(PptGenerationJob).where(
                PptGenerationJob.project_id == p.id,
                PptGenerationJob.status.in_(["queued", "running"]),
            ).order_by(PptGenerationJob.created_at.desc()))
            if existing:
                return self.serialize_generation(existing)
            pages = sorted(p.pages, key=lambda x: x.sort_order)
            p.design_status, p.current_stage = "running", "layout"
            job = PptGenerationJob(project_id=p.id, total_pages=len(pages), status="queued", stage="queued")
            self.db.add(job); self.db.commit(); self.db.refresh(job)
            from app.jobs.dispatcher import stage_and_publish
            task_id = f"ppt-generation:{job.id}"
            job.queue_task_id = task_id
            stage_and_publish(self.db, "ppt_generation", (job.id, p.id, self.user.id), task_id)
            self._event(p, "generation.started", {"job_id": job.id, "total_pages": len(pages)}); self.db.commit()
            return self.serialize_generation(job)


    def start_visual_research(self, project_id: str) -> dict[str, Any]:
        """Queue visual research immediately and return without waiting on providers."""
        p = self.project(project_id)
        with _GENERATION_LOCKS_GUARD:
            lock = _GENERATION_LOCKS.setdefault(f"visual:{p.id}", threading.Lock())
        with lock:
            existing = self.db.scalar(select(PptGenerationJob).where(
                PptGenerationJob.project_id == p.id,
                PptGenerationJob.stage == "visual",
                PptGenerationJob.status.in_(["queued", "running"]),
            ).order_by(PptGenerationJob.created_at.desc()))
            if existing:
                return self.serialize_generation(existing)
            pages = sorted(p.pages, key=lambda x: x.sort_order)
            job = PptGenerationJob(project_id=p.id, total_pages=len(pages), status="queued", stage="visual")
            self.db.add(job); self.db.commit(); self.db.refresh(job)
            from app.jobs.dispatcher import stage_and_publish
            task_id = f"ppt-visual:{job.id}"
            job.queue_task_id = task_id
            stage_and_publish(self.db, "ppt_visual_research", (job.id, p.id, self.user.id), task_id)
            self._event(p, "visual.research.started", {"job_id": job.id, "total_pages": len(pages)}); self.db.commit()
            return self.serialize_generation(job)


    def generation_job(self, project_id: str, job_id: str) -> dict[str, Any]:
        self.project(project_id)
        job = self.db.scalar(select(PptGenerationJob).where(PptGenerationJob.id == job_id, PptGenerationJob.project_id == project_id))
        if not job:
            raise HTTPException(404, "生成任务不存在")
        return self.serialize_generation(job)


    def cancel_generation(self, project_id: str, job_id: str) -> dict[str, Any]:
        self.project(project_id)
        job = self.db.scalar(select(PptGenerationJob).where(PptGenerationJob.id == job_id, PptGenerationJob.project_id == project_id))
        if not job: raise HTTPException(404, "生成任务不存在")
        if job.status in {"queued", "running"}:
            job.status, job.stage = "cancelled", "cancelled"; job.finished_at = datetime.now(timezone.utc)
            self._event(self.project(project_id), "generation.cancelled", {"job_id": job.id}); self.db.commit()
        return self.serialize_generation(job)


    def generate_design(self, project_id: str) -> dict[str, Any]:
        p = self.project(project_id)
        if not p.theme_id:
            raise HTTPException(409, "请先选择主题")
        theme = get_theme(p.theme_id); layout_list = list_layouts(p.theme_id); layouts = {item["id"]: item for item in layout_list}
        pages = sorted(p.pages, key=lambda x: x.sort_order)
        p.design_status = "running"; p.current_stage = "layout"; self._event(p, "design.pipeline.started", {"page_count": len(pages)}); self.db.commit()

        # Ask the model for a whole-deck mapping so layout choices are globally coherent.
        outline = [{"id": page.id, "order": page.sort_order, "section": page.section_title, "title": page.title, "bullets": page.bullets_json or []} for page in pages]
        assignments: dict[str, str] = {}
        try:
            data = ProviderGateway(self.db, self.user.id).json(
                "你是教学课件版式总监。只输出 JSON：{assignments:{page_id:layout_id}}。根据完整大纲为每页选择最合适版式。章节开头用 section；比较/流程/内容较多用 two-column；单一金句或结论用 quote；其余用 title-content。避免连续重复，且只能使用提供的合法布局。",
                {"outline": outline, "layouts": layout_list, "theme": theme["colors"]},
            )
            raw = data.get("assignments") if isinstance(data, dict) else {}
            if isinstance(raw, dict):
                valid = set(layouts)
                assignments = {str(page_id): str(layout_id) for page_id, layout_id in raw.items() if str(page_id) in {x.id for x in pages} and str(layout_id) in valid}
        except Exception:
            assignments = {}
        # Deterministic fallback guarantees the user can always reach the editor.
        for index, page in enumerate(pages):
            if page.id in assignments:
                continue
            bullets = page.bullets_json or []
            title = (page.title or "").lower()
            if index == 0 or (page.section_title and (index == 0 or page.section_title != pages[index - 1].section_title)):
                kind = "section"
            elif len(bullets) <= 1 or any(key in title for key in ("总结", "结论", "关键", "takeaway", "quote")):
                kind = "quote"
            elif len(bullets) >= 5 or any(key in title for key in ("比较", "对比", "流程", "步骤", "方法")):
                kind = "two-column"
            else:
                kind = "title-content"
            assignments[page.id] = next((item["id"] for item in layout_list if item["kind"] == kind), layout_list[0]["id"])
        p.layout_assignments = assignments; p.current_stage = "design"; self._event(p, "layout.assigned", {"assignments": assignments}); self.db.commit()

        quality: list[dict[str, Any]] = []
        for page in pages:
            layout = layouts.get(assignments.get(page.id), layouts.get("title-content")) or layout_list[0]
            document: dict[str, Any]
            try:
                document = self._slide_doc(p, page, "design", layout=layout, outline=outline)
            except Exception:
                document = self._template_document(page, theme, layout)
            if not self._document_quality_ok(document):
                try:
                    repaired = self._slide_doc(p, page, "design_repair", layout=layout, outline=outline)
                    document = repaired if self._document_quality_ok(repaired) else self._template_document(page, theme, layout)
                except Exception:
                    document = self._template_document(page, theme, layout)
            page.design_document_json = document
            page.document_revision += 1
            page.statuses_json = {**(page.statuses_json or {}), "design": "ready"}
            version_no = (self.db.scalar(select(PptDocumentVersion).where(PptDocumentVersion.page_id == page.id).order_by(PptDocumentVersion.version_no.desc())) or PptDocumentVersion(version_no=0)).version_no + 1
            version = PptDocumentVersion(project_id=p.id, page_id=page.id, version_no=version_no, document_json=document)
            self.db.add(version); self.db.flush(); page.current_document_version_id = version.id
            quality.append({"page_id": page.id, "layout_id": layout["id"], "elements": len(document.get("elements") or []), "status": "ok"})
            self._event(p, "page.designed", {"page_id": page.id, "layout_id": layout["id"]})
        self._event(p, "design.quality_checked", {"pages": len(quality), "passed": len(quality)}); p.current_stage = "design"; p.design_status = "ready"; self._event(p, "design.completed", {"page_count": len(pages)}); self.db.commit()
        return {"project": self.serialize_project(p), "pages": [self.serialize_page(page) for page in pages], "assignments": assignments, "quality": quality}

