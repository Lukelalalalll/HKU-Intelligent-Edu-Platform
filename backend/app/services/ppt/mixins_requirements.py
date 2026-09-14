from .context import *  # noqa: F401,F403

class _RequirementsMixin:
    def requirements(self, project_id: str) -> dict[str, Any]:
        p = self.project(project_id)
        req = self.db.scalar(select(PptRequirement).where(PptRequirement.project_id == p.id))
        answers = req.answers_json if req else {}
        return {"project_id": p.id, "status": req.status if req else "pending", "page_count_target": p.page_count_target, "answers": answers, "questions": req.questions_json if req else [], "page_count_options": req.page_count_options_json if req else [], "ready_to_outline": bool(req and req.status == "ready"), "suggested_additions": (answers or {}).get("__suggested_additions", []), "brief_summary": (answers or {}).get("__brief_summary", "")}


    def patch_requirements(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        p = self.project(project_id); req = self.db.scalar(select(PptRequirement).where(PptRequirement.project_id == p.id))
        if not req:
            req = PptRequirement(project_id=p.id); self.db.add(req)
        if payload.get("page_count_target") is not None: p.page_count_target = int(payload["page_count_target"])
        req.answers_json = {**(req.answers_json or {}), **(payload.get("answers") or {})}; self.db.commit()
        return self.requirements(project_id)


    def generate_requirements(self, project_id: str) -> dict[str, Any]:
        p = self.project(project_id); req = self.db.scalar(select(PptRequirement).where(PptRequirement.project_id == p.id))
        gateway = ProviderGateway(self.db, self.user.id)
        data = gateway.json("你是课程课件需求分析师。只输出 JSON：{page_count_options:[{label,page_count,reason}],questions:[{code,label,options:[string]}]}。问题必须帮助教师明确受众、课堂时长和深度。", {"request": p.request_text})
        req.page_count_options_json = data.get("page_count_options", [])[:4]; req.questions_json = data.get("questions", [])[:6]; self.db.commit(); return self.requirements(project_id)


    def _source_context(self, p: PptProject) -> list[dict[str, Any]]:
        processed = self.db.scalars(
            select(FileProcessingChunk)
            .join(FileProcessingDocument, FileProcessingDocument.id == FileProcessingChunk.document_id)
            .join(FileContextBinding, FileContextBinding.document_id == FileProcessingDocument.id)
            .where(
                FileContextBinding.target_type == "ppt_project",
                FileContextBinding.target_id == p.id,
                FileProcessingDocument.status.in_(["ready", "partial_ready"]),
            )
            .order_by(FileProcessingChunk.document_id, FileProcessingChunk.chunk_index)
        ).all()
        if processed:
            context = []
            for chunk in processed:
                document = chunk.document
                metadata = chunk.metadata_json or {}
                context.append({"id": chunk.id, "title": document.filename, "source_type": "file_processing", "collection_id": p.id, "content": chunk.content[:6000], "metadata": {**metadata, "document_id": document.id, "page_number": chunk.page_number, "section": chunk.section}})
            return context
        rows = self.db.scalars(select(PptSourceDocument).join(PptSourceCollection).where(PptSourceCollection.project_id == p.id)).all()
        fingerprint = hashlib.sha1("|".join(f"{x.id}:{len(x.content_md or '')}:{x.title}" for x in rows).encode()).hexdigest()
        cache_key = f"{p.id}:{fingerprint}"
        with _SOURCE_CONTEXT_LOCK:
            cached = _SOURCE_CONTEXT_CACHE.get(cache_key)
        if cached is not None:
            return cached
        context = [{"id": x.id, "title": x.title, "source_type": x.source_type, "collection_id": x.collection_id, "content": (x.content_md or "")[:6000], "metadata": x.metadata_json or {}} for x in rows]
        with _SOURCE_CONTEXT_LOCK:
            for key in [key for key in _SOURCE_CONTEXT_CACHE if key.startswith(f"{p.id}:") and key != cache_key]:
                _SOURCE_CONTEXT_CACHE.pop(key, None)
            _SOURCE_CONTEXT_CACHE[cache_key] = context
        return context


    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        p = self.project(project_id)
        rows = self.db.scalars(select(PptSourceDocument).join(PptSourceCollection).where(PptSourceCollection.project_id == p.id).order_by(PptSourceDocument.id.asc())).all()
        return [{"id": x.id, "title": x.title, "source_type": x.source_type, "metadata": x.metadata_json or {}, "collection_id": x.collection_id} for x in rows]


    def _requirement_input(self, project_id: str, content: str | None, option_id: str | None, option_label: str | None, bootstrap: bool):
        p = self.project(project_id)
        req = self.db.scalar(select(PptRequirement).where(PptRequirement.project_id == p.id))
        if not req:
            req = PptRequirement(project_id=p.id); self.db.add(req); self.db.flush()
        text = (option_label or option_id or content or "").strip()
        if not bootstrap and text:
            self._message(p, "user", text, payload={"option_id": option_id, "option_label": option_label} if option_id else {})
        answers = dict(req.answers_json or {})
        transcript_rows = self.db.scalars(select(PptMessage).where(PptMessage.project_id == p.id, PptMessage.page_id.is_(None)).order_by(PptMessage.created_at.desc()).limit(24)).all()
        transcript = [{"role": m.role, "content": m.content_md} for m in reversed(transcript_rows)]
        return p, req, answers, transcript


    def _apply_requirement_data(self, p: PptProject, req: PptRequirement, answers: dict[str, Any], data: dict[str, Any], fallback: dict[str, Any], attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        patch = data.get("answers_patch") if isinstance(data.get("answers_patch"), dict) else {}
        answers.update({str(k): v for k, v in patch.items() if v not in (None, "")})
        for key in ("page_count_target",):
            if data.get(key) not in (None, ""): answers[key] = data[key]
        suggestions = [str(item) for item in (data.get("suggested_additions") or [])[:4] if str(item).strip()]
        answers["__suggested_additions"] = suggestions
        answers["__brief_summary"] = str(data.get("brief_summary") or fallback["brief_summary"])
        req.answers_json = answers
        req.questions_json = [data["question"]] if isinstance(data.get("question"), dict) else (req.questions_json or [])
        req.status = "ready" if bool(data.get("ready_to_outline")) else "collecting"
        if data.get("page_count_target"):
            try: p.page_count_target = int(data["page_count_target"])
            except (TypeError, ValueError): pass
        ready = req.status == "ready"
        assistant_text = str(data.get("assistant_markdown") or fallback["assistant_markdown"])
        if ready and "生成大纲" not in assistant_text: assistant_text += "\n\n需求已经足够明确，你现在可以点击“生成我的大纲”。如果还有页数、案例或风格偏好，也可以继续补充。"
        payload = {"intent_type": "clarify_requirements", "question": data.get("question"), "answers": answers, "missing_fields": data.get("missing_fields") or [], "ready_to_outline": ready, "suggested_additions": suggestions, "brief_summary": answers["__brief_summary"]}
        assistant = self._message(p, "assistant", assistant_text, payload=payload)
        self.db.commit()
        if attachments is None:
            attachments = self.list_sources(p.id)
        return {"project_id": p.id, "message": {"id": assistant.id, "role": assistant.role, "stage": assistant.stage, "scope_type": assistant.scope_type, "content_md": assistant.content_md, "payload": payload, "created_at": assistant.created_at.isoformat()}, "status": req.status, "answers": answers, "question": data.get("question") if isinstance(data.get("question"), dict) else None, "ready_to_outline": ready, "missing_fields": data.get("missing_fields") or [], "suggested_additions": suggestions, "brief_summary": answers["__brief_summary"], "attachments": attachments}


    def requirement_chat(self, project_id: str, content: str | None = None, option_id: str | None = None, option_label: str | None = None, bootstrap: bool = False) -> dict[str, Any]:
        p, req, answers, transcript = self._requirement_input(project_id, content, option_id, option_label, bootstrap)
        prompt = self._requirement_prompt()
        fallback = self._requirement_fallback()
        sources = self._source_context(p)
        try:
            data = ProviderGateway(self.db, self.user.id).json(prompt, {"request": p.request_text, "answers": answers, "history": transcript, "sources": sources})
        except HTTPException:
            data = fallback
        attachments = [{key: source.get(key) for key in ("id", "title", "source_type", "metadata", "collection_id")} for source in sources]
        return self._apply_requirement_data(p, req, answers, data, fallback, attachments)


    @staticmethod
    def _requirement_prompt() -> str:
        return """你是 PPT 需求访谈 Agent。根据项目描述、资料和对话历史，逐轮帮助教师明确课件需求。只输出 JSON：
    {"assistant_markdown":"...","brief_summary":"用教师口吻总结当前课件需求（1-3句）","question":{"code":"audience|duration|goals|slide_count|other","label":"...","options":["..."]}|null,"answers_patch":{},"missing_fields":["..."],"ready_to_outline":false,"suggested_additions":["..."],"page_count_target":null}
    每轮最多 6 个选项；选项必须是短文本。至少确认受众、教学目标、课堂时长和页数/节奏，不要询问视觉风格，视觉主题由后续步骤人工选择。信息足够时 ready_to_outline=true，并明确告诉教师可以点击生成大纲，但仍给出可补充内容。"""


    @staticmethod
    def _requirement_fallback() -> dict[str, Any]:
        return {"assistant_markdown": "为了做出合适的大纲，还需要确认教学目标和课件节奏。你最希望学生学会什么？", "brief_summary": "正在梳理课件主题、受众与教学节奏。", "question": {"code": "goals", "label": "这套课件最重要的教学目标是什么？", "options": ["理解核心概念", "掌握实践方法", "完成课堂讨论", "准备考试或汇报"]}, "answers_patch": {}, "missing_fields": ["goals"], "ready_to_outline": False, "suggested_additions": [], "page_count_target": None}


    def requirement_chat_stream(self, project_id: str, content: str | None = None, option_id: str | None = None, option_label: str | None = None, bootstrap: bool = False):
        p, req, answers, transcript = self._requirement_input(project_id, content, option_id, option_label, bootstrap)
        prompt, fallback = self._requirement_prompt(), self._requirement_fallback()
        sources = self._source_context(p)
        attachments = [{key: source.get(key) for key in ("id", "title", "source_type", "metadata", "collection_id")} for source in sources]
        try:
            stream = ProviderGateway(self.db, self.user.id).stream_json(prompt, {"request": p.request_text, "answers": answers, "history": transcript, "sources": sources})
            for event in stream:
                if event.get("type") == "chunk":
                    yield event
                elif event.get("type") == "final":
                    yield {"type": "complete", "result": self._apply_requirement_data(p, req, answers, event.get("data") or {}, fallback, attachments)}
        except Exception:
            yield {"type": "complete", "result": self._apply_requirement_data(p, req, answers, fallback, fallback, attachments)}


    def route_message(self, project_id: str, content: str, page_id: str | None = None, option_id: str | None = None, option_label: str | None = None) -> dict[str, Any]:
        p = self.project(project_id)
        if not page_id:
            return self.requirement_chat(project_id, content, option_id, option_label)
        self._message(p, "user", content, page_id)
        decision = ProviderGateway(self.db, self.user.id).json(
            "你是课件工作区 router。只输出 JSON：{action_type,should_execute,reason}. action_type 必须是 page_update_outline_in_search、page_generate_search_queries、page_search_run、page_visual_research、page_visual_plan、page_summary_generate、page_draft_generate、page_design_generate 之一。无法判断时 should_execute=false。",
            {"message": content, "project_stage": p.current_stage, "page_id": page_id},
        )
        if not decision.get("should_execute"):
            assistant = self._message(p, "assistant", decision.get("reason") or "我先把这条需求记下，告诉我希望修改哪一页或先生成哪一步。", page_id, decision)
            self.db.commit()
            return {"decision": decision, "message": {"id": assistant.id, "role": assistant.role, "content_md": assistant.content_md}}
        action = str(decision.get("action_type"))
        if not page_id:
            raise HTTPException(400, "页面级 Agent 动作需要先选择一个页面")
        if action == "page_update_outline_in_search":
            patch = ProviderGateway(self.db, self.user.id).json("只输出 JSON：{title,bullets}，根据用户要求修改当前页面，保留不变的信息。", {"message": content, "current_title": self.page(project_id, page_id).title, "current_bullets": self.page(project_id, page_id).bullets_json})
            result = self.patch_page(project_id, page_id, {"title": patch.get("title") or self.page(project_id, page_id).title, "bullets": patch.get("bullets") or self.page(project_id, page_id).bullets_json})
            self._message(p, "assistant", "已更新当前页结构，研究、初稿和设计稿已标记为待刷新。", page_id, {"action_type": action})
            self.db.commit()
            return {"decision": decision, "result": result}
        result = self.run_action(project_id, page_id, action)
        result["decision"] = decision
        self._message(p, "assistant", "已完成当前页动作。你可以继续修改内容，或让我生成下一阶段产物。", page_id, {"action_type": action, "result": result})
        self.db.commit()
        return result


    def generate_outline(self, project_id: str, page_count_target: int, _legacy_style: str | None = None) -> dict[str, Any]:
        p = self.project(project_id)
        req = self.db.scalar(select(PptRequirement).where(PptRequirement.project_id == p.id))
        if req and req.status != "ready" and p.current_stage == "init":
            raise HTTPException(409, "请先完成需求对话；Agent 确认后才能生成大纲")
        p.page_count_target, p.current_stage = page_count_target, "outline"
        gateway = ProviderGateway(self.db, self.user.id)
        data = gateway.json("你是大学教学课件架构师。只输出 JSON：{sections:[{title,pages:[{title,bullets}]}]}。总页数必须接近目标，页面职责不能重复。", {"request": p.request_text, "page_count": page_count_target})
        pages_payload = [page for section in data.get("sections", []) if isinstance(section, dict) for page in section.get("pages", []) if isinstance(page, dict)]
        if not pages_payload:
            raise HTTPException(502, "模型没有返回有效大纲")
        for old in list(p.pages): self.db.delete(old)
        outline = {"sections": data.get("sections", [])}
        version_no = (self.db.scalar(select(PptOutlineVersion).where(PptOutlineVersion.project_id == p.id).order_by(PptOutlineVersion.version_no.desc())) or PptOutlineVersion(version_no=0)).version_no + 1
        self.db.add(PptOutlineVersion(project_id=p.id, version_no=version_no, outline_json=outline, status="ready"))
        order = 0
        for section in data.get("sections", []):
            for page in section.get("pages", []):
                statuses = {k: ("ready" if k == "outline" else "empty") for k in ("outline", "search", "visual", "summary", "draft", "design")}
                self.db.add(PptPage(project_id=p.id, section_title=section.get("title", ""), sort_order=order, title=page.get("title", "未命名页面"), bullets_json=page.get("bullets", [])[:8], statuses_json=statuses)); order += 1
        p.current_stage = "search"; self.db.commit(); self.db.refresh(p)
        checkpoint = PptCheckpoint(project_id=p.id, checkpoint_code="outline_confirm", stage="outline", status="pending", summary_md="大纲已生成，请确认章节和页数后继续。", payload_json=outline)
        self.db.add(checkpoint); p.latest_checkpoint_code = checkpoint.checkpoint_code
        self._event(p, "outline.completed", {"page_count": order}); self.db.commit()
        return {"project": self.serialize_project(p), "outline": outline, "pages": [self.serialize_page(x) for x in sorted(p.pages, key=lambda x: x.sort_order)]}


    def select_theme(self, project_id: str, theme_id: str) -> dict[str, Any]:
        p = self.project(project_id)
        from app.services.ppt_theme import get_theme
        theme = validate_theme_pack(get_theme(theme_id))
        theme = {**theme, "schema_version": 1, "base_theme": theme.get("base_theme") or theme["id"], "layout_recipes": {layout["id"]: {"roles": layout.get("roles", []), "kind": layout.get("kind")} for layout in list_layouts(theme["id"])}}
        # A theme change invalidates all generated layout/design artifacts.
        p.theme_id = theme["id"]; p.theme_config = theme; p.current_stage = "layout"; p.design_status = "pending"
        p.layout_assignments = {}
        for page in p.pages:
            for version in self.db.scalars(select(PptDocumentVersion).where(PptDocumentVersion.page_id == page.id)).all():
                self.db.delete(version)
            page.design_document_json = None
            page.draft_document_json = None
            page.current_document_version_id = None
            page.document_revision += 1
            page.statuses_json = {**(page.statuses_json or {}), "visual": "stale" if page.visual_plan_json else "empty", "draft": "empty", "design": "empty"}
        self.db.commit()
        return self.serialize_project(p)


    def assign_layouts(self, project_id: str, assignments: dict[str, str] | None = None, mode: str = "manual") -> dict[str, Any]:
        p = self.project(project_id)
        from app.services.ppt_theme import list_layouts
        layouts = list_layouts(p.theme_id or "light-academic")
        valid = {item["id"] for item in layouts}
        current = dict(p.layout_assignments or {})
        if mode == "auto":
            for index, page in enumerate(sorted(p.pages, key=lambda item: item.sort_order)):
                current[page.id] = layouts[index % len(layouts)]["id"]
        else:
            for page_id, layout_id in (assignments or {}).items():
                if self.page(project_id, page_id).id and layout_id in valid:
                    current[page_id] = layout_id
        p.layout_assignments = current
        if p.pages and all(page.id in current for page in p.pages):
            p.current_stage = "design"
        self.db.commit()
        return {"project": self.serialize_project(p), "assignments": current, "layouts": layouts}


    def serialize_generation(job: PptGenerationJob) -> dict[str, Any]:
        return {
            "id": job.id, "project_id": job.project_id, "status": job.status,
            "stage": job.stage, "total_pages": job.total_pages,
            "completed_pages": job.completed_pages, "failed_pages": job.failed_pages,
            "current_page_id": job.current_page_id, "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "updated_at": job.updated_at.isoformat(),
        }

