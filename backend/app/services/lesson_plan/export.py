"""PDF rendering for lesson plans using the installed headless Chromium."""

from __future__ import annotations

import os
from pathlib import Path

INSTALL_HINT = "未找到可用的 Chromium：请执行 `python -m playwright install chromium`（容器内还需安装中文字体）后重试"


class ExportRenderError(RuntimeError):
    """PDF rendering failed for an actionable reason."""


def _fallback_executable() -> str | None:
    """Return a locally cached Chromium when the pinned revision is missing.

    Developer machines often have an older Playwright browser cache than the
    installed Python package expects.  Launching the newest cached binary keeps
    local PDF export working without downloading another browser; deployments
    install the matching revision instead.
    """
    roots: list[Path] = []
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured:
        roots.append(Path(configured))
    roots.extend(
        [
            Path.home() / "Library" / "Caches" / "ms-playwright",
            Path.home() / ".cache" / "ms-playwright",
        ]
    )
    patterns = (
        "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
        "chromium-*/chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-linux/chrome",
    )
    for root in roots:
        for pattern in patterns:
            for candidate in sorted(root.glob(pattern), reverse=True):
                if candidate.is_file():
                    return str(candidate)
    return None


def _launch(playwright):
    """Launch Chromium, falling back to an older cached revision."""
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as exc:  # Playwright raises a generic error for a missing revision
        if "Executable doesn't exist" not in str(exc):
            raise
        fallback = _fallback_executable()
        if not fallback:
            raise
        return playwright.chromium.launch(headless=True, executable_path=fallback)


def render_pdf(html_text: str, output_path: Path) -> None:
    """Render one HTML document into an A4 PDF at ``output_path``.

    Raises:
        ExportRenderError: when Playwright or its browser binary is missing, or
            when Chromium fails to produce the PDF.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ExportRenderError("后端缺少 playwright 依赖，请重新安装 requirements.txt") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = _launch(playwright)
            try:
                page = browser.new_page()
                page.set_content(html_text, wait_until="load")
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
            finally:
                browser.close()
    except ExportRenderError:
        raise
    except Exception as exc:  # Playwright surfaces missing browsers as generic errors
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message.lower():
            raise ExportRenderError(INSTALL_HINT) from exc
        raise ExportRenderError(f"PDF 渲染失败：{message[:300]}") from exc


__all__ = ["ExportRenderError", "INSTALL_HINT", "render_pdf"]
