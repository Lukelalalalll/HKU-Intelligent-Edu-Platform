import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ppt_theme import get_theme, render_slide_svg


def test_custom_document_preview_does_not_add_default_title_or_footer():
    page = SimpleNamespace(
        title="自定义首页标题",
        section_title="自定义章节",
        bullets_json=["默认要点"],
        design_document_json={
            "elements": [
                {"id": "title", "type": "title", "x": 7, "y": 8, "w": 86, "h": 14, "text": "自定义首页标题", "font_size": 34},
                {"id": "body", "type": "body", "x": 9, "y": 30, "w": 80, "h": 8, "text": "自定义正文", "font_size": 19},
            ]
        },
    )

    svg = render_slide_svg(page, get_theme("light-academic"))

    assert svg.count("自定义首页标题") == 1
    assert "自定义正文" in svg
    assert "自定义章节" not in svg


def test_default_preview_keeps_title_and_footer_without_custom_elements():
    page = SimpleNamespace(
        title="默认首页标题",
        section_title="默认章节",
        bullets_json=["默认要点"],
        design_document_json={"elements": []},
    )

    svg = render_slide_svg(page, get_theme("light-academic"))

    assert "<text x=\"80\" y=\"105\" class=\"title\">默认首页标题</text>" in svg
    assert ">默认章节</text>" in svg
