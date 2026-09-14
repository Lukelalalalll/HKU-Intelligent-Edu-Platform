from .context import *  # noqa: F401,F403

class _VisualMixin:
    def preview_svg(self, project_id: str, page_id: str, layout_id: str | None = None) -> str:
        p = self.project(project_id); page = self.page(project_id, page_id)
        from app.services.ppt_theme import get_theme, list_layouts, render_slide_svg
        layouts = {item["id"]: item for item in list_layouts(p.theme_id or "light-academic")}
        selected_layout = layout_id or (p.layout_assignments or {}).get(page.id)
        return render_slide_svg(page, get_theme(p.theme_id or "light-academic"), layouts.get(selected_layout))


    def patch_page(self, project_id: str, page_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        p = self.project(project_id); page = self.page(project_id, page_id)
        page.title, page.bullets_json = payload["title"].strip(), payload.get("bullets", [])[:8]
        if payload.get("section_title") is not None: page.section_title = payload["section_title"]
        if payload.get("speaker_notes") is not None: page.speaker_notes = payload["speaker_notes"]
        statuses = dict(page.statuses_json or {}); statuses.update({"search": "stale" if page.citations_json else "empty", "visual": "stale" if page.visual_plan_json else "empty", "summary": "stale" if page.summary_md else "empty", "draft": "stale" if page.draft_document_json else "empty", "design": "stale" if page.design_document_json else "empty"}); page.statuses_json = statuses
        self.db.commit(); return self.serialize_page(page)


    def delete_page(self, project_id: str, page_id: str) -> dict[str, Any]:
        """Delete a slide and compact the storyboard order."""
        p = self.project(project_id)
        page = self.page(project_id, page_id)
        if len(p.pages) <= 1:
            raise HTTPException(409, "课件至少需要保留一页")
        self.db.delete(page)
        self.db.flush()
        remaining_pages = sorted((item for item in p.pages if item.id != page_id), key=lambda x: x.sort_order)
        for index, item in enumerate(remaining_pages):
            item.sort_order = index
        if p.active_page_id == page_id:
            p.active_page_id = remaining_pages[0].id if remaining_pages else None
        p.page_count_target = self.db.query(PptPage).filter(PptPage.project_id == p.id).count()
        p.design_status = "pending"
        self._event(p, "workspace.data.updated", {"deleted_page_id": page_id})
        self.db.commit()
        return {"project": self.serialize_project(p), "deleted_page_id": page_id}


    def insert_page(self, project_id: str, title: str, bullets: list[str], section_title: str = "", document: dict[str, Any] | None = None) -> dict[str, Any]:
        p = self.project(project_id)
        page = PptPage(
            project_id=p.id,
            section_title=section_title.strip(),
            sort_order=len(p.pages),
            title=title.strip() or "未命名页面",
            bullets_json=[str(item) for item in bullets[:8]],
            statuses_json={"outline": "ready", "search": "empty", "visual": "empty", "summary": "empty", "draft": "empty", "design": "ready" if document else "empty"},
            design_document_json=document,
        )
        self.db.add(page)
        self.db.flush()
        p.page_count_target = self.db.query(PptPage).filter(PptPage.project_id == p.id).count()
        p.design_status = "pending"
        if document:
            self.patch_document(project_id, page.id, document, page.document_revision)
        else:
            self.db.commit()
        return self.serialize_page(page)


    def save_visual_selection(self, project_id: str, page_id: str, asset_ids: list[str]) -> dict[str, Any]:
        page = self.page(project_id, page_id)
        ids = list(dict.fromkeys(str(x) for x in asset_ids))
        if len(ids) > 6:
            raise HTTPException(422, "每页最多选择 6 张图片")
        visual = dict(page.visual_plan_json or {})
        assets = [x for x in (visual.get("asset_manifest") or []) if isinstance(x, dict)]
        known = {str(x.get("id")): x for x in assets}
        unknown = [x for x in ids if x not in known]
        if unknown:
            raise HTTPException(422, "选择的图片不属于当前页面候选集")
        visual["selected_asset_ids"] = ids
        visual["selection_status"] = "confirmed"
        page.visual_plan_json = visual
        page.statuses_json = {**(page.statuses_json or {}), "visual": "ready"}
        self.db.commit()
        return self.serialize_page(page)


    def run_action(self, project_id: str, page_id: str | None, action_type: str, replace_existing: bool = True) -> dict[str, Any]:
        p = self.project(project_id); page = self.page(project_id, page_id) if page_id else None
        if action_type == "project_batch_visual":
            return self.start_visual_research(project_id)
        from app.services.ppt_graph import PptWorkflowGraph
        graph_state = PptWorkflowGraph().invoke({"project_id": p.id, "page_id": page_id, "action_type": action_type})
        decision = graph_state["decision"]
        if not decision["should_execute"]:
            raise HTTPException(400, f"Agent 无法执行该动作：{', '.join(decision['missing_data'])}")
        run = PptAgentRun(project_id=p.id, page_id=page.id if page else None, action_type=action_type, status="running", decision_json=decision); self.db.add(run); self.db.flush(); self._event(p, "agent.router.decision", decision); self._event(p, "agent.run.started", {"run_id": run.id, "action_type": action_type, "page_id": page_id}); self.db.commit()
        try:
            if action_type == "page_generate_search_queries": result = self._page_queries(p, page)
            elif action_type in {"page_search_run", "page_search_refresh"}: result = self._page_search(p, page, replace_existing or action_type.endswith("refresh"))
            elif action_type == "page_visual_research": result = self._visual_research(p, page)
            elif action_type == "page_visual_plan": result = self._visual_plan(p, page)
            elif action_type == "page_summary_generate": result = self._summary(p, page)
            elif action_type == "page_draft_generate": result = self._draft(p, page)
            elif action_type == "page_design_generate": result = self._design(p, page)
            elif action_type.startswith("project_batch_"): result = self._batch(p, action_type)
            else: raise HTTPException(400, "不支持的 Agent 动作")
            run.status = "completed"; self._event(p, "agent.run.completed", {"run_id": run.id, "result": result}); self.db.commit(); return {"run_id": run.id, "status": run.status, "result": result}
        except Exception as exc:
            run.status, run.error_message = "failed", str(exc); self._event(p, "agent.run.failed", {"run_id": run.id, "error": str(exc)}); self.db.commit(); raise


    def _page_queries(self, p: PptProject, page: PptPage) -> dict[str, Any]:
        keywords = extract_keywords(getattr(page, "section_title", ""), page.title, getattr(page, "bullets_json", []) or [], getattr(page, "page_role", ""))
        text = query_text(page.section_title, page.title, page.bullets_json or [], page.page_role)
        queries = [{"query_text": text, "query_purpose": "outline keyword match"}]
        for word in keywords[2:6]:
            queries.append({"query_text": f"{word} {page.page_role or 'concept'}", "query_purpose": "keyword expansion"})
        page.search_queries_json = queries[:6]; page.statuses_json = {**(page.statuses_json or {}), "search": "ready"}; self.db.commit(); return {"queries": page.search_queries_json}


    def _page_search(self, p: PptProject, page: PptPage, replace: bool) -> dict[str, Any]:
        if not page.search_queries_json: self._page_queries(p, page)
        if not settings.search_provider_url:
            # DeepSeek's native web_search is exposed by the Responses API.
            # This keeps page search functional without a second search key.
            results: list[dict[str, Any]] = []
            gateway = ProviderGateway(self.db, self.user.id)
            failures = 0
            def search_one(query):
                try:
                    data = gateway.web_search_json(str(query.get("query_text") or ""))
                    items = data.get("results") or data.get("images") or []
                    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
                except Exception:
                    return None
            # Search calls are already isolated in a durable background job;
            # keeping this loop sequential avoids nested executors and makes
            # provider rate limiting and retry accounting deterministic.
            for query in page.search_queries_json[:6]:
                found = search_one(query)
                if found is None: failures += 1
                else: results.extend(found)
            page.citations_json = self._dedupe_search_results(results)[:30]
            search_status = "failed" if failures and not page.citations_json else "ready" if page.citations_json else "empty"
            page.statuses_json = {**(page.statuses_json or {}), "search": search_status, "visual": "stale"}
            self.db.commit()
            return {"result_count": len(page.citations_json), "failed_queries": failures, "status": search_status, "provider": "deepseek_web_search"}
        import httpx
        results = []
        failures = 0
        headers = {"Authorization": f"Bearer {settings.search_provider_key}"} if settings.search_provider_key else {}
        for q in page.search_queries_json:
            for attempt in range(2):
                try:
                    request_payload = {"query": q["query_text"], "type": "web_and_image"} if attempt == 0 else {"query": q["query_text"]}
                    response = httpx.post(settings.search_provider_url, json=request_payload, headers=headers, timeout=60)
                    response.raise_for_status(); payload = response.json()
                    if isinstance(payload, list):
                        results.extend(payload)
                    else:
                        results.extend(payload.get("results", [])); results.extend(payload.get("images", []))
                    break
                except Exception:
                    if attempt == 1:
                        failures += 1
                        continue
        page.citations_json = self._dedupe_search_results(results)[:30]
        search_status = "failed" if failures and not page.citations_json else "ready"
        page.statuses_json = {**(page.statuses_json or {}), "search": search_status, "visual": "stale"}
        self.db.commit(); return {"result_count": len(page.citations_json), "failed_queries": failures, "status": search_status}


    @staticmethod
    def _wikimedia_image_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Use Wikimedia Commons as a keyless, license-aware image fallback.

        A small public fallback keeps the visual step useful when native search
        cannot return image URLs. A configured provider remains the preferred
        source for richer web/image retrieval.
        """
        if not query.strip():
            return []
        try:
            import httpx

            response = httpx.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": 6,
                    "gsrlimit": max(1, min(limit, 12)),
                    "prop": "imageinfo",
                    "iiprop": "url|mime|size|extmetadata",
                    "iiurlwidth": 1600,
                    "format": "json",
                    "formatversion": 2,
                },
                headers={"User-Agent": "HKU-Courseware-Agent/1.0"},
                timeout=4,
            )
            response.raise_for_status()
            pages = ((response.json() or {}).get("query") or {}).get("pages") or []
            results: list[dict[str, Any]] = []
            for item in pages:
                info = (item.get("imageinfo") or [{}])[0]
                image_url = info.get("thumburl") or info.get("url")
                if not image_url:
                    continue
                metadata = info.get("extmetadata") or {}

                def meta(name: str) -> str:
                    value = metadata.get(name) or {}
                    return str(value.get("value") or "").strip() if isinstance(value, dict) else str(value).strip()

                title = str(item.get("title") or "").removeprefix("File:").strip()
                results.append({
                    "title": title or "Wikimedia Commons image",
                    "image_url": image_url,
                    "url": info.get("descriptionurl") or image_url,
                    "snippet": meta("ImageDescription") or title,
                    "license": meta("LicenseShortName") or "Wikimedia Commons",
                    "score": 0.62,
                    "source": "wikimedia_commons",
                })
            return results
        except Exception:
            return []


    @staticmethod
    def _openverse_image_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Public, attribution-aware image search fallback."""
        if not query.strip():
            return []
        try:
            import httpx
            response = httpx.get("https://api.openverse.org/v1/images/", params={"q": query, "page_size": max(1, min(limit, 20))}, headers={"User-Agent": "HKU-Courseware-Agent/1.0"}, timeout=6)
            response.raise_for_status()
            results = []
            for item in (response.json() or {}).get("results", []):
                image_url = item.get("thumbnail") or item.get("url")
                if not image_url:
                    continue
                results.append({"title": item.get("title") or "Openverse image", "image_url": image_url, "url": item.get("foreign_landing_url") or item.get("url"), "snippet": item.get("description") or item.get("title") or query, "license": item.get("license") or "Openverse", "score": float(item.get("score") or 0.55), "source": "openverse"})
            return results
        except Exception:
            return []


    @staticmethod
    def _dedupe_search_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set(); output: list[dict[str, Any]] = []
        for raw in results:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            key = str(item.get("url") or item.get("link") or item.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key); output.append(item)
        return output


    @staticmethod
    def _image_url(item: dict[str, Any]) -> str:
        for key in ("image_url", "thumbnail", "thumbnail_url", "image", "src", "url"):
            value = item.get(key)
            if isinstance(value, dict):
                value = value.get("url") or value.get("src")
            if isinstance(value, str) and value.startswith(("http://", "https://", "data:")):
                if key == "url" and not re.search(r"\.(png|jpe?g|webp|gif)(\?|$)", value, re.I):
                    continue
                return value
        return ""


    def _download_image(self, p: PptProject, page: PptPage, url: str, index: int) -> dict[str, Any] | None:
        if not url or url.startswith("data:"):
            return {"id": f"asset-{page.id}-{index}", "src": url, "public_url": url, "source_url": url, "status": "ready"} if url else None
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
                return None
            host = parsed_url.hostname.lower()
            if host in {"localhost", "127.0.0.1", "::1"}:
                return None
            try:
                resolved = socket.gethostbyname(host)
                if ipaddress.ip_address(resolved).is_private or ipaddress.ip_address(resolved).is_loopback or ipaddress.ip_address(resolved).is_link_local:
                    return None
            except (OSError, ValueError):
                return None
            import httpx
            response = httpx.get(url, follow_redirects=True, timeout=6, headers={"User-Agent": "HKU-Courseware-Agent/1.0"})
            response.raise_for_status()
            content = response.content
            if len(content) > 8 * 1024 * 1024:
                return None
            content_type = response.headers.get("content-type", "")
            suffix = Path(urlparse(str(response.url)).path).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                suffix = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
            root = settings.ppt_storage_path / p.id / "assets"
            root.mkdir(parents=True, exist_ok=True)
            filename = f"{stable_asset_id(url)}{suffix}"
            path = root / filename
            if not path.exists():
                path.write_bytes(content)
            public_url = f"/api/ppt/projects/{p.id}/assets/{filename}"
            asset = {"id": f"asset-{page.id}-{index}", "src": public_url, "asset_path": str(path), "public_url": public_url, "source_url": url, "mime_type": content_type or mimetypes.guess_type(filename)[0] or "image/jpeg", "status": "ready"}
            # Recognition is deliberately deferred; it must never block image insertion.
            asset["recognition"] = {"status": "pending"}
            return asset
        except Exception as exc:
            return {"id": f"asset-{page.id}-{index}", "source_url": url, "status": "failed", "error": str(exc)[:160]}


    def _recognize_image(self, content: bytes, mime_type: str) -> dict[str, Any]:
        """Best-effort OCR/vision enrichment; never blocks slide generation."""
        try:
            gateway = ProviderGateway(self.db, self.user.id)
            client = gateway._client()
            model = gateway.config.model if gateway.config else settings.llm_model
            response = client.chat.completions.create(model=model, temperature=0.1, messages=[{"role": "user", "content": [{"type": "text", "text": "请识别这张图片：输出 JSON，字段为 description、ocr_text、visual_tags、is_chart。不要猜测无法看清的文字。"}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64.b64encode(content).decode()}"}}]}])
            text = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", text)
                parsed = json.loads(match.group(0)) if match else {"description": text}
            return {"description": str(parsed.get("description") or ""), "ocr_text": str(parsed.get("ocr_text") or ""), "visual_tags": [str(item) for item in (parsed.get("visual_tags") or [])[:8]], "is_chart": bool(parsed.get("is_chart"))}
        except Exception as exc:
            return {"status": "unavailable", "error": str(exc)[:120]}


    def _visual_research(self, p: PptProject, page: PptPage) -> dict[str, Any]:
        if not getattr(page, "search_queries_json", None) and not getattr(page, "citations_json", None):
            self._page_queries(p, page)
        keywords = extract_keywords(getattr(page, "section_title", ""), page.title, getattr(page, "bullets_json", []) or [], getattr(page, "page_role", ""))
        query_text_value = build_query(getattr(page, "section_title", ""), page.title, getattr(page, "bullets_json", []) or [], getattr(page, "page_role", ""))
        raw_results: list[dict[str, Any]] = []
        existing_citations = getattr(page, "citations_json", None) or []
        # Existing citations with direct image URLs are already usable. Avoid
        # replacing a deterministic candidate set with a second network search
        # (and keep retries from duplicating or reordering the same assets).
        has_direct_image = any(isinstance(item, dict) and self._image_url(item) for item in existing_citations)
        if has_direct_image:
            browser_error = ""
            raw_results.extend(existing_citations)
        else:
            try:
                raw_results.extend(BrowserImageSearch(mode=settings.visual_search_mode, proxy=settings.visual_search_proxy or None, timeout=settings.visual_search_timeout_seconds, headless=settings.visual_search_browser_headless, executable_path=settings.visual_search_browser_executable_path or None).search_sync(query_text_value, 12))
            except Exception as exc:
                browser_error = str(exc)[:200]
            else:
                browser_error = ""
            raw_results.extend(existing_citations)
        if not raw_results:
            for query in (page.search_queries_json or [])[:3]:
                text = str(query.get("query_text") or "")
                found = self._wikimedia_image_search(text, 8)
                raw_results.extend(found or self._openverse_image_search(text, 8))
        ranked = rank_candidates(raw_results, keywords, limit=12)
        page.citations_json = self._dedupe_search_results(ranked)
        candidates: list[dict[str, Any]] = []
        for item in page.citations_json or []:
            if not isinstance(item, dict):
                continue
            url = self._image_url(item)
            if not url:
                continue
            if url.startswith("data:"):
                asset = self._download_image(p, page, url, len(candidates) + 1)
            else:
                try:
                    cached = download_image(url, settings.ppt_storage_path / p.id / "assets", f"/api/ppt/projects/{p.id}/assets", max_bytes=settings.visual_search_max_image_bytes, timeout=settings.visual_search_timeout_seconds)
                    asset = {"id": f"asset-{page.id}-{len(candidates)+1}", "source_url": item.get("url") or url, **cached}
                except Exception:
                    # A search result can be a perfectly valid image even when
                    # the backend cannot cache it (hotlink protection, a
                    # transient CDN error, or a content-type mismatch). Keep a
                    # public URL as a degraded candidate so the browser can
                    # still render it and the user can continue with visuals.
                    asset = self._remote_image_asset(url, page, len(candidates) + 1)
            if asset and asset.get("status") == "failed":
                asset = self._remote_image_asset(url, page, len(candidates) + 1)
            if asset:
                asset.update({"title": item.get("title") or page.title, "alt": item.get("snippet") or item.get("title") or page.title, "score": float(item.get("score") or item.get("relevance") or 0.5), "license": item.get("license") or item.get("copyright")})
                candidates.append(asset)
            if len(candidates) >= 6:
                break
        if not candidates:
            # Existing citations may contain web pages but no direct image URL.
            # Keep the image step useful by querying the public image fallback
            # before marking the page as empty.
            queries = page.search_queries_json or [{"query_text": f"{page.title} {page.section_title}".strip()}]
            for query in queries[:1]:
                text = str(query.get("query_text") or "")
                fallback = self._wikimedia_image_search(text, 4) or self._openverse_image_search(text, 4)
                for item in fallback:
                    url = self._image_url(item)
                    asset = self._download_image(p, page, url, len(candidates) + 1) if url else None
                    if asset and asset.get("status") == "failed":
                        asset = self._remote_image_asset(url, page, len(candidates) + 1)
                    if asset:
                        asset.update({"title": item.get("title") or page.title, "alt": item.get("snippet") or item.get("title") or page.title, "score": float(item.get("score") or 0.5), "license": item.get("license")})
                        candidates.append(asset)
                    if len(candidates) >= 6:
                        break
                if len(candidates) >= 6:
                    break
        visual = dict(page.visual_plan_json or {})
        # A new candidate set requires an explicit user confirmation again.
        if hasattr(page, "search_queries_json"):
            visual["selected_asset_ids"] = []
            visual["selection_status"] = "pending"
        candidates = rerank(candidates, query_text(getattr(page, "section_title", ""), page.title, getattr(page, "bullets_json", []) or [], getattr(page, "page_role", "")), getattr(settings, "clip_model_name", ""))
        visual["asset_manifest"] = candidates[:6]
        visual["asset_query"] = query_text(getattr(page, "section_title", ""), page.title, getattr(page, "bullets_json", []) or [], getattr(page, "page_role", ""))
        visual["asset_status"] = "ready" if candidates else ("failed" if browser_error else "empty")
        if browser_error and not candidates: visual["asset_error"] = browser_error
        page.visual_plan_json = visual
        page.statuses_json = {**(page.statuses_json or {}), "visual": "ready" if candidates else "empty"}
        self.db.commit()
        return {"asset_count": len(candidates), "assets": candidates, "status": visual["asset_status"]}

