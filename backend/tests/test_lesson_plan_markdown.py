"""Markdown rendering and export builder coverage for the lesson plan agent."""

from app.services.lesson_plan.markdown import (
    build_export_html,
    build_markdown_export,
    render_markdown,
    strip_answer_blocks,
)


PROJECT = {"title": "牛顿第二定律", "subject": "物理", "grade": "中四", "duration_minutes": 45}
PAGES = [
    {
        "title": "学习目标",
        "sort_order": 0,
        "document": {"version": 2, "markdown": "- 理解牛顿第二定律\n- 能运用 F=ma 解题"},
    },
    {
        "title": "课堂练习",
        "sort_order": 1,
        "document": {
            "version": 2,
            "markdown": (
                "1. 基础题\n2. 进阶题\n\n"
                "| 物理量 | 符号 |\n| --- | --- |\n| 力 | F |\n\n"
                "> [!answer] 参考答案\n> a = 2 m/s²\n\n"
                "> [!tip] 提示\n> 注意单位统一。"
            ),
        },
    },
]


def test_render_markdown_supports_headings_lists_tables_and_callouts():
    html = render_markdown(PAGES[1]["document"]["markdown"])
    assert "<ol>" in html and "<li>" in html
    assert "<table>" in html and "<th>物理量</th>" in html
    assert "callout-answer" in html and "参考答案" in html
    assert "callout-tip" in html and "提示" in html


def test_render_markdown_escapes_raw_html():
    html = render_markdown("<script>alert(1)</script> **safe**")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<strong>safe</strong>" in html


def test_answer_blocks_are_hidden_when_disabled():
    markdown = PAGES[1]["document"]["markdown"]
    visible = render_markdown(markdown, True)
    hidden = render_markdown(markdown, False)
    assert "参考答案" in visible
    assert "参考答案" not in hidden
    assert "提示" in hidden
    assert "参考答案" not in strip_answer_blocks(markdown)


def test_markdown_export_includes_pages_and_honours_answer_toggle():
    exported = build_markdown_export(PROJECT, PAGES, True)
    assert exported.startswith("# 牛顿第二定律")
    assert "## 01 学习目标" in exported and "## 02 课堂练习" in exported
    assert "参考答案" in exported
    without = build_markdown_export(PROJECT, PAGES, False)
    assert "参考答案" not in without


def test_export_html_contains_a4_pages_and_black_white_class():
    html = build_export_html(PROJECT, PAGES, True, True)
    assert 'class="is-bw"' in html
    assert html.count('<section class="sheet">') == 2
    assert "@page" in html and "A4" in html
    assert "牛顿第二定律" in html
