from .context import *  # noqa: F401,F403

class _CoreMixin:
    def project(self, project_id: str) -> PptProject:
        item = self.db.scalar(select(PptProject).where(PptProject.id == project_id, PptProject.owner_id == self.user.id))
        if not item:
            raise HTTPException(404, "PPT 项目不存在")
        return item


    def page(self, project_id: str, page_id: str) -> PptPage:
        item = self.db.scalar(select(PptPage).where(PptPage.id == page_id, PptPage.project_id == project_id))
        if not item or item.project.owner_id != self.user.id:
            raise HTTPException(404, "页面不存在")
        return item


    def serialize_project(self, p: PptProject) -> dict[str, Any]:
        pages = sorted(p.pages, key=lambda item: item.sort_order)
        if p.theme_id:
            base_theme = get_theme(p.theme_id)
            theme = validate_theme_pack({**base_theme, **(p.theme_config or {}), "colors": {**(base_theme.get("colors") or {}), **((p.theme_config or {}).get("colors") or {})}, "tokens": {**(base_theme.get("tokens") or {}), **((p.theme_config or {}).get("tokens") or {})}})
        else:
            theme = p.theme_config or {}
        return {"id": p.id, "title": p.title, "request_text": p.request_text, "course_id": p.course_id, "current_stage": p.current_stage, "status": p.status, "active_page_id": p.active_page_id, "latest_checkpoint_code": p.latest_checkpoint_code, "page_count_target": p.page_count_target, "theme_id": p.theme_id, "theme_config": theme, "layout_assignments": p.layout_assignments or {}, "design_status": p.design_status, "page_count": len(pages), "cover_preview_url": preview_filename(p.id, pages[0].id) if pages else None, "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat()}


    def delete_project(self, project_id: str) -> None:
        project = self.project(project_id)
        project_root = settings.ppt_storage_path / project.id
        export_path = settings.ppt_storage_path / f"{project.id}.pptx"
        self.db.delete(project)
        self.db.commit()
        if project_root.is_dir():
            shutil.rmtree(project_root)
        if export_path.is_file():
            export_path.unlink()


    def serialize_page(self, p: PptPage) -> dict[str, Any]:
        statuses = dict(p.statuses_json or {})
        document = p.design_document_json or p.draft_document_json
        if isinstance(document, dict):
            # v2 documents remain readable, but all API consumers see the
            # current protocol marker and canvas contract immediately.
            document = {**document, "version": 3, "canvas": {"width": 1280, "height": 720}}
        visual_plan = p.visual_plan_json or {}
        return {"id": p.id, "project_id": p.project_id, "section_title": p.section_title, "sort_order": p.sort_order, "title": p.title, "bullets": p.bullets_json or [], "statuses": statuses, "search_queries": p.search_queries_json or [], "summary_md": p.summary_md, "citations": p.citations_json or [], "document": document, "document_revision": p.document_revision, "current_document_version_id": p.current_document_version_id, "speaker_notes": p.speaker_notes, "page_role": p.page_role, "content_plan": p.content_plan_json or {}, "visual_plan": visual_plan, "asset_manifest": visual_plan.get("asset_manifest", []), "image_slots": visual_plan.get("image_slots", []), "selected_asset_ids": visual_plan.get("selected_asset_ids", []), "preview_url": preview_filename(p.project_id, p.id) if document else None, "layout_id": (p.project.layout_assignments or {}).get(p.id), "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat()}


    def list_projects(self) -> list[dict[str, Any]]:
        return [self.serialize_project(p) for p in self.db.scalars(select(PptProject).where(PptProject.owner_id == self.user.id).order_by(PptProject.updated_at.desc()))]


    def create_project(self, title: str, request_text: str, course_id: str | None = None) -> dict[str, Any]:
        p = PptProject(owner_id=self.user.id, title=title.strip() or "未命名课件", request_text=request_text.strip(), course_id=course_id)
        self.db.add(p); self.db.flush()
        self.db.add(PptRequirement(project_id=p.id))
        self._message(p, "user", p.request_text, payload={"intent_type": "initial_request"})
        self._message(p, "assistant", "好的，我先帮你把课件需求梳理清楚。先确认一下：这套 PPT 主要面向什么对象？例如本科生、研究生、教师培训或企业客户。", payload={
            "intent_type": "clarify_requirements",
            "question": {"code": "audience", "label": "这套 PPT 主要面向什么对象？", "options": ["本科生", "研究生", "教师培训", "企业客户"]},
            "ready_to_outline": False,
        })
        self._event(p, "project.created", {"stage": "init"})
        self.db.commit(); self.db.refresh(p)
        return self.serialize_project(p)


    def list_messages(self, project_id: str, page_id: str | None = None) -> list[dict[str, Any]]:
        p = self.project(project_id)
        query = select(PptMessage).where(PptMessage.project_id == p.id)
        if page_id is not None: query = query.where(PptMessage.page_id == page_id)
        rows = self.db.scalars(query.order_by(PptMessage.created_at.desc()).limit(100)).all()
        rows.reverse()
        return [{"id": x.id, "role": x.role, "stage": x.stage, "scope_type": x.scope_type, "page_id": x.page_id, "content_md": x.content_md, "payload": x.structured_payload_json or {}, "created_at": x.created_at.isoformat()} for x in rows]


    def list_checkpoints(self, project_id: str) -> list[dict[str, Any]]:
        p = self.project(project_id)
        rows = self.db.scalars(select(PptCheckpoint).where(PptCheckpoint.project_id == p.id).order_by(PptCheckpoint.created_at.desc())).all()
        return [{"id": x.id, "checkpoint_code": x.checkpoint_code, "stage": x.stage, "status": x.status, "summary_md": x.summary_md, "payload": x.payload_json or {}, "created_at": x.created_at.isoformat()} for x in rows]


    def _message(self, p: PptProject, role: str, content: str, page_id: str | None = None, payload: dict | None = None) -> PptMessage:
        item = PptMessage(project_id=p.id, page_id=page_id, role=role, stage=p.current_stage, scope_type="page" if page_id else "project", content_md=content, structured_payload_json=payload or {})
        self.db.add(item); self.db.flush(); return item


    def confirm_checkpoint(self, project_id: str, code: str, note: str | None = None) -> dict[str, Any]:
        p = self.project(project_id)
        checkpoint = self.db.scalar(select(PptCheckpoint).where(PptCheckpoint.project_id == p.id, PptCheckpoint.checkpoint_code == code, PptCheckpoint.status == "pending").order_by(PptCheckpoint.created_at.desc()))
        if not checkpoint:
            raise HTTPException(404, "确认点不存在或已处理")
        checkpoint.status = "confirmed"
        if note: checkpoint.summary_md = f"{checkpoint.summary_md}\n{note}".strip()
        p.latest_checkpoint_code = None
        # Confirmation is an explicit transition, never a hidden side effect
        # of generating the next artifact.
        if code == "outline_confirm":
            p.current_stage = "visual"
            p.status = "active"
        elif code.endswith("_confirm"):
            p.status = "active"
        self.db.commit()
        return self.serialize_project(p)


    def patch_document(self, project_id: str, page_id: str, document: dict[str, Any], revision: int) -> dict[str, Any]:
        p = self.project(project_id); page = self.page(project_id, page_id)
        if revision != page.document_revision:
            raise HTTPException(409, "页面已被更新，请刷新后重试")
        # Normalize editor payloads at the API boundary so every element has a
        # stable id and bounded geometry before it becomes a new version.
        normalized = dict(document or {})
        normalized["version"] = 3
        normalized["canvas"] = {"width": 1280, "height": 720}
        elements = []
        for index, raw in enumerate(normalized.get("elements") or []):
            item = dict(raw or {})
            item["id"] = str(item.get("id") or f"element-{index + 1}")
            for key in ("x", "y", "w", "h"):
                try:
                    item[key] = max(0.0, min(100.0, float(item.get(key, 0))))
                except (TypeError, ValueError):
                    item[key] = 0.0
            item.setdefault("type", "body")
            item["x"] = max(0.0, min(100.0, item["x"]))
            item["y"] = max(0.0, min(100.0, item["y"]))
            item["w"] = max(0.1, min(100.0 - item["x"], item["w"]))
            item["h"] = max(0.1, min(100.0 - item["y"], item["h"]))
            try:
                item["rotation"] = float(item.get("rotation", 0) or 0) % 360
            except (TypeError, ValueError):
                item["rotation"] = 0
            item["opacity"] = max(0.0, min(1.0, float(item.get("opacity", 1) or 1)))
            item["visible"] = item.get("visible", True) is not False
            item.setdefault("zIndex", index + 1)
            if item.get("type") == "image": item.setdefault("object_fit", "cover")
            elements.append(item)
        normalized["elements"] = elements
        page.document_revision += 1
        page.design_document_json = normalized
        page.statuses_json = {**(page.statuses_json or {}), "design": "ready"}
        version_no = (self.db.scalar(select(PptDocumentVersion).where(PptDocumentVersion.page_id == page.id).order_by(PptDocumentVersion.version_no.desc())) or PptDocumentVersion(version_no=0)).version_no + 1
        version = PptDocumentVersion(project_id=p.id, page_id=page.id, version_no=version_no, document_json=normalized)
        self.db.add(version); self.db.flush(); page.current_document_version_id = version.id
        self._event(p, "workspace.data.updated", {"page_id": page.id, "revision": page.document_revision})
        self.db.commit(); return self.serialize_page(page)


    def restore_document(self, project_id: str, page_id: str, revision: int, direction: str) -> dict[str, Any]:
        p = self.project(project_id); page = self.page(project_id, page_id)
        if revision != page.document_revision:
            raise HTTPException(409, "页面已被更新，请刷新后重试")
        versions = self.db.scalars(select(PptDocumentVersion).where(PptDocumentVersion.page_id == page.id).order_by(PptDocumentVersion.version_no.asc())).all()
        if not versions:
            raise HTTPException(409, "当前页面没有可恢复版本")
        current_no = next((v.version_no for v in versions if v.id == page.current_document_version_id), versions[-1].version_no)
        target_no = current_no - 1 if direction == "undo" else current_no + 1
        target = next((v for v in versions if v.version_no == target_no), None)
        if not target:
            raise HTTPException(409, "没有更多可恢复的版本")
        page.design_document_json = target.document_json
        page.document_revision += 1
        page.current_document_version_id = target.id
        self._event(p, "workspace.data.updated", {"page_id": page.id, "revision": page.document_revision, "direction": direction})
        self.db.commit()
        return self.serialize_page(page)


    def _event(self, p: PptProject, event_type: str, payload: dict[str, Any]) -> None:
        self.db.add(PptAgentEvent(project_id=p.id, event_type=event_type, payload_json=payload))

