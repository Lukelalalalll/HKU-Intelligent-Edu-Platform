"""Tool-driven assistant used by the preview/editor workspace."""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.services.ppt_agent import PptAgentService, ProviderGateway
from app.services.ppt_theme import get_theme, list_layouts


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}


TOOLS: list[dict[str, Any]] = [
    _tool("getPresentationOutline", "读取当前课件的页面顺序、标题和要点。", {}),
    _tool("getSlideAtIndex", "读取指定页的完整内容。slide_index 从 0 开始。", {"slide_index": {"type": "integer"}}, ["slide_index"]),
    _tool("searchSlides", "按关键词搜索当前课件页面。", {"query": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]),
    _tool("researchSlideVisuals", "为指定页面联网检索并识别可用图片，返回素材候选和来源。", {"slide_index": {"type": "integer"}}, ["slide_index"]),
    _tool("planSlideLayout", "根据页面角色、主题和素材候选生成可解释的视觉版式计划。", {"slide_index": {"type": "integer"}}, ["slide_index"]),
    _tool("getAvailableLayouts", "读取当前主题可用的页面布局。", {}),
    _tool("saveSlide", "保存一页完整文档；content 必须是 JSON 对象。可替换现有页或新增页面。", {"slide_index": {"type": "integer"}, "content": {"type": "object"}, "replace_existing": {"type": "boolean"}, "title": {"type": "string"}, "bullets": {"type": "array", "items": {"type": "string"}}, "section_title": {"type": "string"}}, ["content"]),
    _tool("updateSlideOutline", "只修改页面标题、要点或备注。", {"slide_index": {"type": "integer"}, "title": {"type": "string"}, "bullets": {"type": "array", "items": {"type": "string"}}, "speaker_notes": {"type": "string"}}, ["slide_index"]),
    _tool("deleteSlide", "删除指定页面。仅在用户明确要求删除时使用。", {"slide_index": {"type": "integer"}}, ["slide_index"]),
    _tool("setPresentationTheme", "切换整套课件主题。仅在用户明确要求时使用。", {"theme_id": {"type": "string"}}, ["theme_id"]),
    _tool("updateSlideColors", "修改当前页的颜色。整页/背景色请求必须设置 background_color；不要只修改一个文字元素。", {"slide_index": {"type": "integer"}, "background_color": {"type": "string"}, "accent_color": {"type": "string"}, "title_color": {"type": "string"}, "body_color": {"type": "string"}, "scope": {"type": "string", "enum": ["background", "accent", "title", "body", "all"]}}, ["slide_index"]),
]


SYSTEM_PROMPT = """你是 PPT Generator 的预览编辑助手。请用用户的语言回答，简洁、准确、行动导向。
当前课件的实时数据库状态优先于历史对话。用户说第 N 页时，工具索引使用 N-1。
涉及当前页面内容、顺序、布局或修改时必须先读取实时状态；修改必须调用工具保存，不要只描述计划。
用户要求配图、联网找图、优化排版时，先调用 researchSlideVisuals，再调用 planSlideLayout；没有可用图片时接受 icon/shape/text-only 降级。
saveSlide 的 content 必须保留未修改元素并符合 canvas 1280x720；保存成功后再向用户报告。
当用户说“这一页颜色改为某色”“页面背景色”“整页换色”时，默认理解为背景色，必须调用 updateSlideColors 的 background_color；不能把颜色只写到 section/装饰文字上。
多页修改必须逐页读取、保存并确认；无法确定目标页时只询问一个澄清问题。
不要索要 API Key，也不要把内部工具参数暴露给用户。"""


class PptEditAgent:
    def __init__(self, service: PptAgentService):
        self.service = service
        self.gateway = ProviderGateway(service.db, service.user.id)

    def _context(self, project_id: str, page_id: str | None) -> dict[str, Any]:
        project = self.service.project(project_id)
        pages = sorted(project.pages, key=lambda item: item.sort_order)
        current = self.service.page(project_id, page_id) if page_id else None
        return {
            "project": {"title": project.title, "request": project.request_text, "theme_id": project.theme_id},
            "pages": [{"index": i, "id": p.id, "title": p.title, "section": p.section_title, "bullets": p.bullets_json or []} for i, p in enumerate(pages)],
            "current_slide": self.service.serialize_page(current) if current else None,
        }

    def _page_at(self, project_id: str, index: int):
        pages = sorted(self.service.project(project_id).pages, key=lambda item: item.sort_order)
        if index < 0 or index >= len(pages):
            raise HTTPException(400, f"页面索引超出范围：{index}")
        return pages[index]

    @staticmethod
    def _direct_color_args(content: str, page_id: str | None) -> dict[str, Any] | None:
        """Handle unambiguous Chinese color requests deterministically.

        This prevents a vague request such as “这一页改成黄色” from being
        interpreted as changing one decorative label by the language model.
        """
        if not page_id or not re.search(r"颜色|配色|背景|换色", content):
            return None
        match = re.search(r"(?:改为|改成|换成|设置为|变为)\s*(黄色|黄|橙色|橙|红色|红|蓝色|蓝|绿色|绿|紫色|紫|黑色|黑|白色|白|#[0-9a-fA-F]{3,8})", content)
        if not match:
            return None
        color = {"黄色": "#f2c94c", "黄": "#f2c94c", "橙色": "#f2994a", "橙": "#f2994a", "红色": "#eb5757", "红": "#eb5757", "蓝色": "#2f80ed", "蓝": "#2f80ed", "绿色": "#27ae60", "绿": "#27ae60", "紫色": "#9b51e0", "紫": "#9b51e0", "黑色": "#111827", "黑": "#111827", "白色": "#ffffff", "白": "#ffffff"}.get(match.group(1), match.group(1))
        scope = "title" if re.search(r"标题|题目", content) else "body" if re.search(r"正文|要点|文字", content) else "accent" if re.search(r"强调|装饰", content) else "background"
        return {"slide_index": 0, "background_color": color if scope == "background" else "", "title_color": color if scope == "title" else "", "body_color": color if scope == "body" else "", "accent_color": color if scope == "accent" else "", "scope": scope}

    def execute(self, project_id: str, page_id: str | None, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "getPresentationOutline":
            return {"ok": True, "pages": self._context(project_id, page_id)["pages"]}
        if name == "getSlideAtIndex":
            return {"ok": True, "slide": self.service.serialize_page(self._page_at(project_id, int(args.get("slide_index", 0))))}
        if name == "searchSlides":
            query = str(args.get("query", "")).lower().strip()
            limit = max(1, min(20, int(args.get("limit", 8))))
            pages = sorted(self.service.project(project_id).pages, key=lambda item: item.sort_order)
            hits = [{"index": i, "id": p.id, "title": p.title, "bullets": p.bullets_json or []} for i, p in enumerate(pages) if query in (p.title + " " + " ".join(p.bullets_json or [])).lower()]
            return {"ok": True, "matches": hits[:limit]}
        if name == "researchSlideVisuals":
            page = self._page_at(project_id, int(args.get("slide_index", 0)))
            return {"ok": True, "slide": self.service.serialize_page(page), "visual": self.service._visual_research(self.service.project(project_id), page)}
        if name == "planSlideLayout":
            project = self.service.project(project_id)
            page = self._page_at(project_id, int(args.get("slide_index", 0)))
            return {"ok": True, "slide": self.service.serialize_page(page), "visual": self.service._visual_plan(project, page)}
        if name == "getAvailableLayouts":
            project = self.service.project(project_id)
            return {"ok": True, "layouts": list_layouts(project.theme_id or "light-academic")}
        if name == "updateSlideOutline":
            page = self._page_at(project_id, int(args.get("slide_index", 0)))
            payload = {"title": str(args.get("title") or page.title), "bullets": args.get("bullets") if isinstance(args.get("bullets"), list) else page.bullets_json, "speaker_notes": args.get("speaker_notes", page.speaker_notes)}
            updated = self.service.patch_page(project_id, page.id, payload)
            # Keep the live preview in sync even when the model chooses the
            # lightweight outline tool instead of saveSlide.
            if page.design_document_json:
                document = dict(page.design_document_json)
                elements = [dict(item) for item in (document.get("elements") or [])]
                title_element = next((item for item in elements if item.get("type") == "title"), None)
                if title_element:
                    title_element["text"] = payload["title"]
                body_elements = [item for item in elements if item.get("type") == "body"]
                for index, item in enumerate(body_elements):
                    if index < len(payload["bullets"]):
                        item["text"] = f"• {payload['bullets'][index]}"
                document["elements"] = elements
                updated = self.service.patch_document(project_id, page.id, document, page.document_revision)
            return {"ok": True, "slide": updated}
        if name == "saveSlide":
            content = args.get("content")
            if not isinstance(content, dict):
                raise HTTPException(400, "saveSlide content 必须是 JSON 对象")
            replace = bool(args.get("replace_existing", True))
            if replace:
                page = self._page_at(project_id, int(args.get("slide_index", 0)))
                return {"ok": True, "saved": True, "slide": self.service.patch_document(project_id, page.id, content, page.document_revision)}
            slide = self.service.insert_page(project_id, str(args.get("title") or "未命名页面"), args.get("bullets") if isinstance(args.get("bullets"), list) else [], str(args.get("section_title") or ""), content)
            return {"ok": True, "saved": True, "slide": slide}
        if name == "deleteSlide":
            page = self._page_at(project_id, int(args.get("slide_index", 0)))
            return {"ok": True, "deleted": True, **self.service.delete_page(project_id, page.id)}
        if name == "setPresentationTheme":
            theme_id = str(args.get("theme_id") or "")
            # Validate before mutating so the model cannot silently select an invalid theme.
            get_theme(theme_id)
            return {"ok": True, "project": self.service.select_theme(project_id, theme_id)}
        if name == "updateSlideColors":
            page = self._page_at(project_id, int(args.get("slide_index", 0)))
            document = dict(page.design_document_json or {})
            document["theme"] = dict(document.get("theme") or {})
            aliases = {"background_color": "background", "accent_color": "accent", "title_color": "title", "body_color": "body"}
            colors: dict[str, str] = {}
            for argument, key in aliases.items():
                value = str(args.get(argument) or "").strip()
                if value:
                    if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", value):
                        raise HTTPException(400, f"颜色值无效：{value}")
                    colors[key] = value
            if not colors:
                raise HTTPException(400, "至少需要提供一种颜色")
            document["theme"].update(colors)
            if "background" in colors:
                document["theme"]["bg"] = colors["background"]
            scope = str(args.get("scope") or "all")
            for element in document.get("elements") or []:
                if scope in {"accent", "all"} and "accent" in colors and str(element.get("type") or "").lower() in {"shape", "icon", "rect", "rectangle", "rounded-rectangle", "rounded_rectangle", "roundrect", "card", "panel", "box", "bar", "divider", "line", "rule", "circle", "oval", "ellipse", "decoration"}:
                    # Normalize the paint field so both the SVG preview and
                    # native PPTX exporter receive the same accent colour.
                    element["fill"] = colors["accent"]
                if scope in {"title", "all"} and "title" in colors and element.get("type") == "title":
                    element["color"] = colors["title"]
                if scope in {"body", "all"} and "body" in colors and element.get("type") in {"body", "caption"}:
                    element["color"] = colors["body"]
            saved = self.service.patch_document(project_id, page.id, document, page.document_revision)
            return {"ok": True, "saved": True, "slide": saved, "colors": colors}
        raise HTTPException(400, f"不支持的 Agent 工具：{name}")

    def run(self, project_id: str, page_id: str | None, content: str, history: list[dict[str, Any]] | None = None) -> Iterator[dict[str, Any]]:
        direct_color = self._direct_color_args(content, page_id)
        if direct_color:
            if page_id:
                ordered_ids = [item.id for item in sorted(self.service.project(project_id).pages, key=lambda item: item.sort_order)]
                direct_color["slide_index"] = ordered_ids.index(page_id) if page_id in ordered_ids else 0
            scope_label = {"background": "背景色", "title": "标题色", "body": "正文色", "accent": "强调色"}[direct_color["scope"]]
            yield {"type": "trace", "trace": {"kind": "tool_call", "round": 1, "tool": "updateSlideColors", "status": "start", "slideIndex": direct_color["slide_index"], "message": f"正在更新页面{scope_label}"}}
            try:
                result = self.execute(project_id, page_id, "updateSlideColors", direct_color)
                yield {"type": "trace", "trace": {"kind": "tool_call", "round": 1, "tool": "updateSlideColors", "status": "success", "slideIndex": direct_color["slide_index"], "message": f"页面{scope_label}已更新"}}
                selected_color = next(value for key, value in (("background", direct_color["background_color"]), ("title", direct_color["title_color"]), ("body", direct_color["body_color"]), ("accent", direct_color["accent_color"])) if value)
                yield {"type": "chunk", "chunk": f"已将当前页{scope_label}更新为{selected_color}。"}
            except Exception as exc:
                yield {"type": "trace", "trace": {"kind": "tool_call", "round": 1, "tool": "updateSlideColors", "status": "error", "slideIndex": direct_color["slide_index"], "message": str(exc)}}
                yield {"type": "chunk", "chunk": f"配色更新失败：{exc}"}
            return
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, * (history or []), {"role": "user", "content": content}]
        messages[0]["content"] += "\n实时课件状态：" + json.dumps(self._context(project_id, page_id), ensure_ascii=False)
        client = self.gateway._client()
        model = self.gateway.config.model if self.gateway.config else settings.llm_model
        for round_no in range(8):
            response = client.chat.completions.create(model=model, temperature=0.2, messages=messages, tools=TOOLS, tool_choice="auto")
            message = response.choices[0].message
            calls = list(message.tool_calls or [])
            if not calls:
                text = message.content or "已完成处理。"
                for chunk in [text[i:i + 80] for i in range(0, len(text), 80)]:
                    yield {"type": "chunk", "chunk": chunk}
                return
            assistant_message = {"role": "assistant", "content": message.content or "", "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]}
            messages.append(assistant_message)
            for call in calls:
                name = call.function.name
                call_args: dict[str, Any] = {}
                yield {"type": "trace", "trace": {"kind": "tool_call", "round": round_no + 1, "tool": name, "status": "start", "message": f"正在执行 {name}"}}
                try:
                    call_args = json.loads(call.function.arguments or "{}")
                    result = self.execute(project_id, page_id, name, call_args)
                    status = "success"
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                    status = "error"
                yield {"type": "trace", "trace": {"kind": "tool_call", "round": round_no + 1, "tool": name, "status": status, "message": f"{name} {'完成' if status == 'success' else '失败'}", **({"slideIndex": call_args.get("slide_index")} if isinstance(call_args.get("slide_index"), int) else {})}}
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
        yield {"type": "chunk", "chunk": "已达到本轮编辑操作上限，请根据已完成的修改继续操作。"}
