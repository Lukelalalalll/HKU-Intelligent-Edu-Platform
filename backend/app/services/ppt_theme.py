from __future__ import annotations

import html
import re
from typing import Any


THEMES: list[dict[str, Any]] = [
    {"id": "business", "name": "Business", "description": "Classic business deck with strong hierarchy.", "family": "Business", "colors": {"bg": "#102a43", "surface": "#1f4e79", "title": "#ffffff", "body": "#d9eaf7", "accent": "#62b0e8"}},
    {"id": "business-clean", "name": "Business Clean", "description": "Balanced spacing and practical layout for lectures.", "family": "Business", "colors": {"bg": "#f5f8fb", "surface": "#ffffff", "title": "#17324d", "body": "#486581", "accent": "#2f80ed"}},
    {"id": "classic", "name": "Classic", "description": "Traditional classroom look with familiar structure.", "family": "Classic", "colors": {"bg": "#fffdf8", "surface": "#f4ead5", "title": "#4a3426", "body": "#6b5546", "accent": "#b7791f"}},
    {"id": "classic-seminar", "name": "Classic Seminar", "description": "Academic tone for theory-heavy courses.", "family": "Classic", "colors": {"bg": "#f7faf9", "surface": "#e3f1ec", "title": "#173f32", "body": "#416654", "accent": "#087250"}},
    {"id": "dark", "name": "Dark", "description": "High-contrast dark visuals for projection rooms.", "family": "Dark", "colors": {"bg": "#111827", "surface": "#1f2937", "title": "#f9fafb", "body": "#cbd5e1", "accent": "#22d3ee"}},
    {"id": "dark-neon", "name": "Dark Neon", "description": "Bold accent dark style for modern topics.", "family": "Dark", "colors": {"bg": "#160f24", "surface": "#2b1d44", "title": "#f5f3ff", "body": "#ddd6fe", "accent": "#c084fc"}},
    {"id": "light", "name": "Light", "description": "Bright and readable for everyday teaching.", "family": "Light", "colors": {"bg": "#ffffff", "surface": "#f1f5f9", "title": "#0f172a", "body": "#475569", "accent": "#0f766e"}},
    {"id": "light-academic", "name": "Light Academic", "description": "Paper-like look for dense conceptual material.", "family": "Light", "colors": {"bg": "#fbfefc", "surface": "#eaf7ef", "title": "#075b42", "body": "#1d3e32", "accent": "#087250"}},
]

LAYOUTS = [
    {"id": "title-content", "name": "Title and Content", "kind": "content", "capacity": "medium", "roles": ["concept", "example", "summary"]},
    {"id": "two-column", "name": "Two Column", "kind": "columns", "capacity": "high", "roles": ["compare", "process", "concept"]},
    {"id": "quote", "name": "Big Quote", "kind": "quote", "capacity": "low", "roles": ["quote", "takeaway"]},
    {"id": "section", "name": "Section Divider", "kind": "section", "capacity": "minimal", "roles": ["section"]},
]


def get_theme(theme_id: str) -> dict[str, Any]:
    key = (theme_id or "light-academic").strip().lower()
    return next((dict(t) for t in THEMES if t["id"] == key), dict(THEMES[-1]))


def list_themes() -> list[dict[str, Any]]:
    return [dict(theme, layout_count=len(LAYOUTS)) for theme in THEMES]


def list_layouts(theme_id: str) -> list[dict[str, Any]]:
    get_theme(theme_id)
    return [dict(layout) for layout in LAYOUTS]


def _safe(value: Any) -> str:
    return html.escape(str(value or ""))


def _svg_text(element: dict[str, Any], colors: dict[str, str]) -> str:
    x = float(element.get("x", 0)) * 12.8
    y = float(element.get("y", 0)) * 7.2
    width = max(24.0, float(element.get("w", 80)) * 12.8)
    size = float(element.get("font_size", 24)) * 1.2
    color = element.get("color") or colors.get("body", "#1d3e32")
    text = str(element.get("text") or "\n".join(element.get("items") or ""))
    max_chars = max(8, int(width / max(size * 0.54, 1)))
    lines = []
    for source_line in (text.splitlines() or [""]):
        while len(source_line) > max_chars:
            lines.append(source_line[:max_chars]); source_line = source_line[max_chars:]
        lines.append(source_line)
    weight = _safe(element.get("font_weight") or (800 if element.get("type") == "title" else 500))
    anchor = {"center": "middle", "right": "end"}.get(str(element.get("align") or "left"), "start")
    anchor_x = x + width / 2 if anchor == "middle" else x + width if anchor == "end" else x
    spans = "".join(f'<tspan x="{anchor_x:.1f}" dy="{0 if i == 0 else size * 1.3:.1f}">{_safe(line)}</tspan>' for i, line in enumerate(lines))
    return f'<text x="{anchor_x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font:{weight} {size:.1f}px Arial;fill:{_safe(color)};opacity:{float(element.get("opacity", 1))}">{spans}</text>'


_SVG_VISUAL_TYPES = {
    "shape", "rect", "rectangle", "rounded-rectangle", "rounded_rectangle",
    "roundrect", "card", "panel", "box", "bar", "divider", "line", "rule",
    "circle", "oval", "ellipse", "background", "decoration",
}


def _svg_visual(element: dict[str, Any], colors: dict[str, str]) -> bool:
    kind = str(element.get("type") or "").strip().lower().replace(" ", "-")
    if kind in _SVG_VISUAL_TYPES:
        return True
    return not (element.get("text") or element.get("items")) and any(element.get(key) not in (None, "") for key in ("fill", "fill_color", "background", "background_color", "stroke", "stroke_color", "shape"))


def _svg_shape(element: dict[str, Any], colors: dict[str, str]) -> str:
    kind = str(element.get("type") or "shape").strip().lower().replace(" ", "-")
    shape_hint = str(element.get("shape") or "").strip().lower().replace("_", "-")
    x, y = float(element.get("x", 0)) * 12.8, float(element.get("y", 0)) * 7.2
    width, height = max(0.1, float(element.get("w", 20)) * 12.8), max(0.1, float(element.get("h", 10)) * 7.2)
    fill = element.get("fill") or element.get("fill_color") or element.get("background") or element.get("background_color")
    stroke = element.get("stroke") or element.get("stroke_color") or element.get("border_color")
    if (kind in {"line", "divider", "rule", "bar"} or shape_hint in {"line", "divider", "rule", "bar"}) and not fill:
        fill = stroke or colors.get("accent")
    fill = fill or colors.get("surface") or colors.get("accent")
    radius = float(element.get("radius", 0) or 0)
    opacity = float(element.get("opacity", 1) or 1)
    if kind in {"circle", "oval", "ellipse"} or shape_hint in {"circle", "oval", "ellipse"}:
        return f'<ellipse cx="{x + width / 2:.1f}" cy="{y + height / 2:.1f}" rx="{width / 2:.1f}" ry="{height / 2:.1f}" fill="{_safe(fill)}" stroke="{_safe(stroke)}" opacity="{opacity}" />'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{radius:.1f}" fill="{_safe(fill)}" stroke="{_safe(stroke)}" opacity="{opacity}" />'


def render_slide_svg(page: Any, theme: dict[str, Any], layout: dict[str, Any] | None = None) -> str:
    base_colors = dict(theme.get("colors") or THEMES[-1]["colors"])
    title = _safe(page.title)
    bullets = [str(x) for x in (page.bullets_json or [])[:6]]
    document = getattr(page, "design_document_json", None) or {}
    # A saved page document may intentionally override the deck theme (for
    # example, when the preview assistant changes one page's background).
    document_theme = document.get("theme") if isinstance(document, dict) else None
    if isinstance(document_theme, dict):
        base_colors.update({key: value for key, value in document_theme.items() if key in {"bg", "surface", "title", "body", "accent"} and value})
        for alias in ("background", "background_color"):
            if document_theme.get(alias):
                base_colors["bg"] = document_theme[alias]
        if document_theme.get("surface_color"):
            base_colors["surface"] = document_theme["surface_color"]
    colors = base_colors
    raw_custom_elements = document.get("elements") if isinstance(document, dict) else None
    custom_elements = [item for item in raw_custom_elements if isinstance(item, dict)] if isinstance(raw_custom_elements, list) else []
    if custom_elements:
        rendered: list[str] = []
        for item in custom_elements:
            kind = str(item.get("type") or "").strip().lower()
            if kind == "image" or (kind == "icon" and item.get("src")):
                rendered.append(f'<image href="{_safe(item.get("src"))}" x="{float(item.get("x", 0)) * 12.8:.1f}" y="{float(item.get("y", 0)) * 7.2:.1f}" width="{float(item.get("w", 20)) * 12.8:.1f}" height="{float(item.get("h", 20)) * 7.2:.1f}" preserveAspectRatio="{"xMidYMid slice" if item.get("object_fit", "cover") == "cover" else "xMidYMid meet"}" opacity="{float(item.get("opacity", 1))}"/>')
            elif _svg_visual(item, colors):
                rendered.append(_svg_shape(item, colors))
            else:
                rendered.append(_svg_text(item, colors))
        body = "".join(rendered)
    else:
        layout_kind = (layout or {}).get("kind", "content")
    if not custom_elements and layout_kind == "section":
        body = f'<text x="72" y="310" class="section">{title}</text>'
    elif not custom_elements and layout_kind == "quote":
        quote = _safe(bullets[0] if bullets else page.title)
        body = f'<text x="100" y="300" class="quote">“{quote}”</text>'
    elif not custom_elements and layout_kind in {"columns", "two-column"}:
        left = bullets[:3]; right = bullets[3:]
        body = ''.join(f'<text x="90" y="{220+i*58}" class="body">• {_safe(item)}</text>' for i, item in enumerate(left))
        body += ''.join(f'<text x="700" y="{220+i*58}" class="body">• {_safe(item)}</text>' for i, item in enumerate(right))
        body += '<line x1="650" y1="180" x2="650" y2="610" class="divider" />'
    elif not custom_elements:
        body = ''.join(f'<text x="100" y="{220+i*58}" class="body">• {_safe(item)}</text>' for i, item in enumerate(bullets))
    default_title = f'<text x="80" y="105" class="title">{title}</text>' if not custom_elements else ""
    default_footer = f'<text x="80" y="675" style="font:16px Arial;fill:{colors["accent"]}">{_safe(page.section_title)}</text>' if not custom_elements else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="{colors["bg"]}"/><rect x="0" y="0" width="18" height="720" fill="{colors["accent"]}"/>
<style>.title{{font:700 42px Arial;fill:{colors["title"]}}}.body{{font:24px Arial;fill:{colors["body"]}}}.section{{font:700 64px Arial;fill:{colors["title"]}}}.quote{{font:italic 36px Arial;fill:{colors["title"]}}}.divider{{stroke:{colors["accent"]};stroke-width:2}}</style>
{default_title}{body}{default_footer}</svg>'''


def preview_filename(project_id: str, page_id: str) -> str:
    return f"/api/ppt/projects/{project_id}/pages/{page_id}/preview.svg"
