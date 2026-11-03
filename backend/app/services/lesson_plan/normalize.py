"""Validation and normalization for model-produced lesson plan payloads.

Models occasionally drift from the requested JSON shape.  Every value that is
persisted or rendered passes through these helpers so a stray field can never
inflate the database, escape into HTML or break the workspace.
"""

from __future__ import annotations

import re
from typing import Any

from .prompts import PAGE_ROLES

MAX_PAGES = 6
MAX_PAGE_MARKDOWN = 20000
MAX_TITLE = 60
MAX_PAGE_TITLE = 24
MAX_LIST_ITEMS = 8

_DIFFICULTIES = {"basic", "standard", "challenge"}


def _text(value: Any, limit: int) -> str:
    """Return a stripped string clipped to ``limit`` characters."""
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _bool(value: Any, default: bool) -> bool:
    """Interpret common truthy encodings without surprising coercions."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "是", "含答案"}:
            return True
        if lowered in {"false", "0", "no", "n", "否", "不含答案"}:
            return False
    return default


def _int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _string_list(value: Any, limit: int = MAX_LIST_ITEMS, item_limit: int = 120) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    output: list[str] = []
    for item in value:
        text = _text(item, item_limit)
        if text and text not in output:
            output.append(text)
        if len(output) >= limit:
            break
    return output


def coerce_page_count(value: Any, default: int = 4) -> int:
    """Clamp a requested page count into the supported range."""
    return _int(value, default, 1, MAX_PAGES)


def coerce_include_answers(value: Any, default: bool = True) -> bool:
    """Coerce the answer-inclusion flag."""
    return _bool(value, default)


def normalize_answers_patch(value: Any) -> dict[str, Any]:
    """Validate the ``answers_patch`` object of an interview turn."""
    patch = value if isinstance(value, dict) else {}
    output: dict[str, Any] = {}
    if "grade" in patch:
        output["grade"] = _text(patch.get("grade"), 80)
    if "subject" in patch:
        output["subject"] = _text(patch.get("subject"), 80)
    if "objectives" in patch:
        objectives = _string_list(patch.get("objectives"))
        if objectives:
            output["objectives"] = objectives
    if "activities" in patch:
        activities = _string_list(patch.get("activities"))
        if activities:
            output["activities"] = activities
    if "duration_minutes" in patch:
        output["duration_minutes"] = _int(patch.get("duration_minutes"), 45, 5, 300)
    if "page_count" in patch:
        output["page_count"] = coerce_page_count(patch.get("page_count"))
    if "include_answers" in patch:
        output["include_answers"] = coerce_include_answers(patch.get("include_answers"))
    if "difficulty" in patch:
        difficulty = _text(patch.get("difficulty"), 20).lower()
        output["difficulty"] = difficulty if difficulty in _DIFFICULTIES else "standard"
    if "notes" in patch:
        output["notes"] = _text(patch.get("notes"), 2000)
    return output


def normalize_question(value: Any) -> dict[str, Any] | None:
    """Validate a single interview question with clickable options."""
    if not isinstance(value, dict):
        return None
    label = _text(value.get("label"), 200)
    if not label:
        return None
    options = _string_list(value.get("options"), limit=6, item_limit=40)
    return {"code": _text(value.get("code"), 40) or "other", "label": label, "options": options}


def normalize_interview(data: Any) -> dict[str, Any]:
    """Validate the interview payload, filling safe defaults."""
    payload = data if isinstance(data, dict) else {}
    assistant_markdown = _text(payload.get("assistant_markdown"), 6000)
    if not assistant_markdown:
        assistant_markdown = "我已经记录这条需求，请继续补充学案信息。"
    ready = bool(payload.get("ready_to_generate"))
    question = normalize_question(payload.get("question"))
    if ready:
        question = None
    return {
        "assistant_markdown": assistant_markdown,
        "brief_summary": _text(payload.get("brief_summary"), 600),
        "question": question,
        "answers_patch": normalize_answers_patch(payload.get("answers_patch")),
        "missing_fields": _string_list(payload.get("missing_fields"), limit=8, item_limit=40),
        "ready_to_generate": ready,
        "suggested_additions": _string_list(payload.get("suggested_additions"), limit=4, item_limit=120),
        "__asked_code": _text(payload.get("__asked_code"), 40) or None,
        "__fallback_reason": _text(payload.get("__fallback_reason"), 300),
    }


def strip_leading_title(markdown: str, title: str) -> str:
    """Remove a first heading that merely repeats the page title."""
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^#{1,4}\s+(.*)$", stripped)
        if match and match.group(1).strip() == (title or "").strip():
            return "\n".join(lines[:index] + lines[index + 1:]).strip()
        break
    return markdown


def _normalize_page(value: Any, fallback_title: str) -> dict[str, Any] | None:
    page = value if isinstance(value, dict) else {}
    markdown = _text(page.get("markdown"), MAX_PAGE_MARKDOWN)
    if not markdown:
        return None
    role = _text(page.get("page_role"), 40)
    if role not in PAGE_ROLES:
        role = "content"
    title = _text(page.get("title"), MAX_PAGE_TITLE) or fallback_title
    markdown = strip_leading_title(markdown, title)
    if not markdown:
        return None
    return {
        "title": title,
        "page_role": role,
        "markdown": markdown,
    }


def normalize_plan(data: Any, *, page_count: int, include_answers: bool) -> dict[str, Any]:
    """Validate a generation payload.

    Raises:
        ValueError: when no usable page survives validation.
    """
    payload = data if isinstance(data, dict) else {}
    raw_pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
    pages: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_pages[:MAX_PAGES + 2], 1):
        page = _normalize_page(raw, f"第 {index} 页")
        if page:
            pages.append(page)
    if not pages:
        raise ValueError("模型没有返回可用的学案页面")
    pages = pages[: max(1, coerce_page_count(page_count, len(pages)))]
    title = _text(payload.get("title"), MAX_TITLE) or "未命名学案"
    duration = _int(payload.get("duration_minutes"), 45, 5, 300)
    return {
        "title": title,
        "subject": _text(payload.get("subject"), 80),
        "grade": _text(payload.get("grade"), 80),
        "duration_minutes": duration,
        "summary_markdown": _text(payload.get("summary_markdown"), 4000),
        "pages": pages,
        "__degraded": False,
        "__include_answers": include_answers,
    }


def normalize_page(data: Any) -> dict[str, Any]:
    """Validate a single rewritten page.

    Raises:
        ValueError: when the page has no markdown.
    """
    payload = data if isinstance(data, dict) else {}
    markdown = _text(payload.get("markdown"), MAX_PAGE_MARKDOWN)
    if not markdown:
        raise ValueError("模型没有返回页面内容")
    role = _text(payload.get("page_role"), 40)
    if role not in PAGE_ROLES:
        role = "content"
    return {
        "title": _text(payload.get("title"), MAX_PAGE_TITLE) or "学案页面",
        "page_role": role,
        "markdown": markdown,
    }


def normalize_page_updates(data: Any, allowed_page_ids: set[str]) -> list[dict[str, str]]:
    """Keep only well-formed updates for pages the project actually owns."""
    payload = data if isinstance(data, dict) else {}
    updates = payload.get("page_updates") if isinstance(payload.get("page_updates"), list) else []
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in updates:
        if not isinstance(raw, dict):
            continue
        page_id = _text(raw.get("page_id"), 40)
        markdown = _text(raw.get("markdown"), MAX_PAGE_MARKDOWN)
        if not page_id or page_id not in allowed_page_ids or not markdown or page_id in seen:
            continue
        seen.add(page_id)
        output.append({"page_id": page_id, "markdown": markdown})
        if len(output) >= 8:
            break
    return output


def normalize_document(document: Any) -> dict[str, Any]:
    """Validate the page document saved by the editor.

    Raises:
        ValueError: when the payload is not the version-2 markdown document.
    """
    payload = document if isinstance(document, dict) else {}
    markdown = _text(payload.get("markdown"), MAX_PAGE_MARKDOWN)
    if not markdown:
        raise ValueError("页面内容不能为空")
    return {"version": 2, "markdown": markdown}


def document_markdown(document: Any) -> str:
    """Return page markdown, keeping a read-only fallback for legacy canvas docs."""
    payload = document if isinstance(document, dict) else {}
    markdown = payload.get("markdown")
    if isinstance(markdown, str) and markdown.strip():
        return markdown.strip()
    elements = payload.get("elements")
    if isinstance(elements, list):
        lines: list[str] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            text = _text(element.get("text"), 4000)
            if not text:
                continue
            if element.get("type") == "title":
                lines.append(f"## {text}")
            else:
                lines.append(text)
        return "\n\n".join(lines)
    return ""


def slug_filename(title: str, fallback: str = "lesson-plan") -> str:
    """Build an ASCII file stem without leaking punctuation into headers."""
    ascii_part = re.sub(r"[^A-Za-z0-9]+", "-", (title or "").lower()).strip("-")
    ascii_part = re.sub(r"-{2,}", "-", ascii_part)[:60].strip("-")
    return ascii_part if len(ascii_part) >= 3 else fallback


__all__ = [
    "MAX_PAGE_MARKDOWN",
    "MAX_PAGES",
    "coerce_include_answers",
    "coerce_page_count",
    "document_markdown",
    "normalize_answers_patch",
    "normalize_document",
    "normalize_interview",
    "normalize_page",
    "normalize_page_updates",
    "normalize_plan",
    "normalize_question",
    "slug_filename",
    "strip_leading_title",
]
