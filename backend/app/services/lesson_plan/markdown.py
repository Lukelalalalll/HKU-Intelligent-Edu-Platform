"""Server-side Markdown rendering and export builders.

The lesson plan stores page content as Markdown.  This module turns it into
the HTML used by the printable PDF and into the downloadable Markdown export.
Only a small, teacher-friendly subset is supported; raw HTML is escaped so
model or teacher content can never inject markup into the export.
"""

from __future__ import annotations

import html
import re
from typing import Any

from .normalize import document_markdown

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_UL = re.compile(r"^[-*+]\s+(.*)$")
_OL = re.compile(r"^\d+[.)]\s+(.*)$")
_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_CALLOUT = re.compile(r"^\[!(tip|note|warning|answer)\]\s*(.*)$", re.IGNORECASE)
_CALLOUT_LABELS = {"tip": "提示", "note": "说明", "warning": "注意", "answer": "参考答案"}


def escape_html(value: Any) -> str:
    """Escape text for safe HTML interpolation."""
    return html.escape(str(value or ""), quote=False)


def render_inline(text: str) -> str:
    """Render inline emphasis and code after escaping the source text."""
    escaped = escape_html(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def strip_answer_blocks(markdown: str) -> str:
    """Remove ``> [!answer]`` callouts from a Markdown document."""
    lines = str(markdown or "").splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith(">"):
            block: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                block.append(lines[index].strip()[1:].lstrip())
                index += 1
            first = block[0] if block else ""
            match = _CALLOUT.match(first)
            if match and match.group(1).lower() == "answer":
                continue
            output.extend(f"> {line}" if line else ">" for line in block)
            continue
        output.append(lines[index])
        index += 1
    return "\n".join(output).strip()


def _render_callout(lines: list[str], include_answers: bool) -> str:
    """Render a collected blockquote, respecting the answer toggle."""
    first = lines[0] if lines else ""
    match = _CALLOUT.match(first)
    if not match:
        body = _render_lines(lines, include_answers)
        return f"<blockquote>{body}</blockquote>"
    tone = match.group(1).lower()
    label = match.group(2).strip() or _CALLOUT_LABELS.get(tone, "")
    if tone == "answer" and not include_answers:
        return ""
    remainder = _render_lines(lines[1:], include_answers)
    label_html = f'<div class="callout-label">{escape_html(label)}</div>' if label else ""
    return f'<div class="callout callout-{tone}">{label_html}{remainder}</div>'


def _render_table(header: list[str], rows: list[list[str]]) -> str:
    """Render one pipe table."""
    head = "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
    body_rows = []
    for row in rows:
        cells = list(row) + [""] * max(0, len(header) - len(row))
        body_rows.append("<tr>" + "".join(f"<td>{render_inline(cell)}</td>" for cell in cells[: len(header)]) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _split_row(line: str) -> list[str]:
    """Split one pipe-table row into trimmed cells."""
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _is_special_line(line: str) -> bool:
    """Return whether a line starts a non-paragraph block."""
    stripped = line.strip()
    return bool(
        not stripped
        or stripped.startswith(">")
        or stripped.startswith("```")
        or _HEADING.match(stripped)
        or _UL.match(stripped)
        or _OL.match(stripped)
        or _HR.match(stripped)
        or "|" in stripped
    )


def _render_lines(lines: list[str], include_answers: bool) -> str:
    """Render a block sequence into HTML."""
    parts: list[str] = []
    index = 0
    total = len(lines)
    while index < total:
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            index += 1
            buffer: list[str] = []
            while index < total and not lines[index].strip().startswith("```"):
                buffer.append(escape_html(lines[index].rstrip()))
                index += 1
            if index < total:
                index += 1
            parts.append("<pre><code>" + "\n".join(buffer) + "</code></pre>")
            continue
        heading = _HEADING.match(stripped)
        if heading:
            level = min(max(len(heading.group(1)) + 1, 2), 4)
            parts.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            index += 1
            continue
        if _HR.match(stripped):
            parts.append("<hr/>")
            index += 1
            continue
        if stripped.startswith(">"):
            block: list[str] = []
            while index < total and lines[index].strip().startswith(">"):
                block.append(lines[index].strip()[1:].lstrip())
                index += 1
            parts.append(_render_callout(block, include_answers))
            continue
        if "|" in stripped and index + 1 < total and _TABLE_SEPARATOR.match(lines[index + 1].strip()):
            header = _split_row(raw)
            rows: list[list[str]] = []
            index += 2
            while index < total and "|" in lines[index] and lines[index].strip():
                rows.append(_split_row(lines[index]))
                index += 1
            parts.append(_render_table(header, rows))
            continue
        unordered = _UL.match(stripped)
        ordered = _OL.match(stripped)
        if unordered or ordered:
            is_ordered = bool(ordered)
            items: list[str] = []
            while index < total:
                candidate = lines[index].strip()
                match = _OL.match(candidate) if is_ordered else _UL.match(candidate)
                if not match:
                    break
                items.append(match.group(1))
                index += 1
            tag = "ol" if is_ordered else "ul"
            parts.append(f"<{tag}>" + "".join(f"<li>{render_inline(item)}</li>" for item in items) + f"</{tag}>")
            continue
        paragraph: list[str] = []
        while index < total and not _is_special_line(lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        if paragraph:
            parts.append("<p>" + "<br/>".join(render_inline(line) for line in paragraph) + "</p>")
        else:
            index += 1
    return "".join(parts)


def render_markdown(markdown: str, include_answers: bool = True) -> str:
    """Render page Markdown into HTML."""
    return _render_lines(str(markdown or "").splitlines(), include_answers)


def page_markdown(page: dict[str, Any]) -> str:
    """Read the Markdown source of a serialized page."""
    return document_markdown(page.get("document") if isinstance(page, dict) else None)


def _field(source: Any, name: str, default: str = "") -> str:
    """Read a project field from a model or a serialized dict."""
    if isinstance(source, dict):
        value = source.get(name)
    else:
        value = getattr(source, name, None)
    return default if value in (None, "") else str(value)


def _page_list(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return pages sorted by ``sort_order`` when the field is present."""
    return sorted(pages, key=lambda page: int(page.get("sort_order") or 0))


def build_markdown_export(project: Any, pages: list[dict[str, Any]], include_answers: bool) -> str:
    """Build the downloadable Markdown lesson plan."""
    title = _field(project, "title", "未命名学案")
    ordered = _page_list(pages)
    meta = [
        f"学科：{_field(project, 'subject')}" if _field(project, "subject") else "",
        f"年级：{_field(project, 'grade')}" if _field(project, "grade") else "",
        f"共 {len(ordered)} 页",
    ]
    meta_line = " ｜ ".join(item for item in meta if item)
    lines = [f"# {title}", ""]
    if meta_line:
        lines += [f"> {meta_line}", ""]
    lines += ["---", ""]
    for index, page in enumerate(ordered, 1):
        page_title = str(page.get("title") or f"第 {index} 页")
        markdown = page_markdown(page)
        if not include_answers:
            markdown = strip_answer_blocks(markdown)
        lines += [f"## {index:02d} {page_title}", "", markdown.strip(), "", "---", ""]
    return "\n".join(lines).rstrip() + "\n"


_EXPORT_CSS = """
@page{size:A4;margin:0}
:root{--ink:#163d31;--muted:#5f7a6d;--accent:#087250;--soft:#eef8f2;--line:#dcebe3}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:"Noto Sans CJK SC","Noto Sans SC","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;color:var(--ink);font-size:11.2pt;line-height:1.65;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sheet{padding:15mm 15mm 14mm;page-break-after:always;border-top:5mm solid var(--accent)}
.sheet:last-child{page-break-after:auto}
.sheet-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:14px}
.sheet-eyebrow{font-size:8pt;letter-spacing:.16em;font-weight:800;color:var(--accent)}
.sheet-title{font-size:19pt;margin:3px 0 0;letter-spacing:-.02em;line-height:1.25}
.sheet-meta{font-size:9pt;color:var(--muted);text-align:right;line-height:1.55;white-space:nowrap}
.sheet-body h2{font-size:14.5pt;margin:14px 0 6px;color:var(--accent)}
.sheet-body h3{font-size:12.5pt;margin:12px 0 5px}
.sheet-body h4{font-size:11.5pt;margin:10px 0 4px}
.sheet-body p{margin:7px 0}
.sheet-body ul,.sheet-body ol{margin:7px 0;padding-left:20px}
.sheet-body li{margin:3px 0}
.sheet-body hr{border:0;border-top:1px dashed var(--line);margin:12px 0}
.sheet-body table{width:100%;border-collapse:collapse;margin:10px 0;font-size:10pt}
.sheet-body th,.sheet-body td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.sheet-body thead th{background:var(--soft)}
.sheet-body code{background:var(--soft);border-radius:3px;padding:1px 4px;font-size:9.6pt}
.sheet-body pre{background:var(--soft);border-radius:6px;padding:10px;white-space:pre-wrap}
.callout{border-radius:8px;padding:8px 11px;margin:10px 0;background:var(--soft);border-left:3px solid var(--accent)}
.callout-label{font-weight:800;font-size:9.5pt;color:var(--accent);margin-bottom:3px}
.callout-answer{background:#fff8e8;border-left-color:#b98a2e}
.callout-answer .callout-label{color:#8a6417}
.callout-warning{background:#fdf1ef;border-left-color:#c0563f}
.sheet-foot{display:flex;justify-content:space-between;gap:12px;margin-top:16px;padding-top:6px;border-top:1px solid var(--line);font-size:8.5pt;color:var(--muted)}
body.is-bw{--ink:#111;--muted:#555;--accent:#333;--soft:#f2f2f2;--line:#c9c9c9}
body.is-bw .callout-answer{background:#f2f2f2;border-left-color:#777}
body.is-bw .callout-answer .callout-label{color:#444}
"""


def build_export_html(project: Any, pages: list[dict[str, Any]], include_answers: bool, black_white: bool) -> str:
    """Build the printable A4 HTML document for the PDF renderer."""
    title = _field(project, "title", "未命名学案")
    subject = _field(project, "subject")
    grade = _field(project, "grade")
    duration_raw = _field(project, "duration_minutes")
    duration = f"{duration_raw} 分钟" if duration_raw else ""
    meta_bits = [bit for bit in (subject, grade, duration) if bit]
    meta = " · ".join(meta_bits)
    ordered = _page_list(pages)
    total = len(ordered)
    sheets: list[str] = []
    for index, page in enumerate(ordered, 1):
        page_title = str(page.get("title") or f"第 {index} 页")
        markdown = page_markdown(page)
        if not include_answers:
            markdown = strip_answer_blocks(markdown)
        body = render_markdown(markdown, include_answers)
        meta_html = f'<div class="sheet-meta">{escape_html(meta)}<br/>{index} / {total}</div>' if meta else f'<div class="sheet-meta">{index} / {total}</div>'
        sheets.append(
            '<section class="sheet">'
            '<header class="sheet-head"><div>'
            f'<div class="sheet-eyebrow">HKU · LESSON PLAN</div>'
            f'<h1 class="sheet-title">{escape_html(page_title)}</h1>'
            "</div>"
            f"{meta_html}"
            "</header>"
            f'<div class="sheet-body">{body}</div>'
            f'<footer class="sheet-foot"><span>{escape_html(title)}</span><span>{index} / {total}</span></footer>'
            "</section>"
        )
    classes = " class=\"is-bw\"" if black_white else ""
    return (
        "<!doctype html><html lang=\"zh-Hans\"><head><meta charset=\"utf-8\"/>"
        f"<title>{escape_html(title)}</title><style>{_EXPORT_CSS}</style></head>"
        f"<body{classes}>{''.join(sheets)}</body></html>"
    )


__all__ = [
    "build_export_html",
    "build_markdown_export",
    "escape_html",
    "page_markdown",
    "render_inline",
    "render_markdown",
    "strip_answer_blocks",
]
