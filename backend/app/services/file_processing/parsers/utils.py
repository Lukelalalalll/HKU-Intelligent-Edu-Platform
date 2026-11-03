"""Low-level extraction helpers shared by the concrete parsers.

Everything here returns the normalized page/block structure consumed by
``_pages_to_chunks``; optional third-party parsers are imported lazily so
the API can start without them.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from app.core.config import settings

def _clean_text(value: str) -> str:
    """Join hyphenated line breaks and collapse soft wraps."""
    value = re.sub(r"-\s*\n\s*", "", str(value or ""))
    return re.sub(r"(?<!\n)[ \t]*\n[ \t]*", " ", value).strip()

def _block(page: int, index: int, typ: str, text: str, source: str, confidence: float = .9, bbox: list[float] | None = None, **meta: Any) -> dict:
    """Build the normalized block dict used by every parser.

    ``markdown`` is derived from the block type so formulas, code and headings
    keep a renderable representation.
    """
    value = text if typ in {"code", "formula"} else _clean_text(text)
    markdown = value
    if typ == "formula": markdown = f"$$\n{value.strip('$ ').strip()}\n$$" if value.strip() else ""
    if typ == "code": markdown = f"```text\n{value}\n```"
    if typ == "heading": markdown = f"### {value}"
    return {"id": f"p{page}-b{index}", "page_number": page, "type": typ, "raw_text": text, "text": value, "markdown": markdown, "bbox": bbox or [0, 0, 1, 1], "bbox_raw": meta.pop("bbox_raw", bbox or [0, 0, 1, 1]), "confidence": confidence, "source": source, **meta}



def _native_pdf(path: Path) -> list[dict]:
    """Extract PDF text and image blocks with PyMuPDF.

    Falls back to pypdf when PyMuPDF is unavailable.
    """
    pages: list[dict] = []
    try:
        import fitz  # type: ignore
        pdf = fitz.open(path)
        for number, page in enumerate(pdf, 1):
            blocks = []
            for index, raw in enumerate(page.get_text("dict").get("blocks", []), 1):
                if raw.get("type") != 0:
                    continue
                text = "\n".join("".join(span.get("text", "") for span in line.get("spans", [])) for line in raw.get("lines", [])).strip()
                if not text:
                    continue
                typ = "heading" if len(text) < 160 and any(span.get("size", 0) >= 14 for line in raw.get("lines", []) for span in line.get("spans", [])) else "text"
                blocks.append(_block(number, index, typ, text, "native_pdf", .96, [max(0, raw.get("bbox", [0, 0, 1, 1])[0] / max(page.rect.width, 1)), max(0, raw.get("bbox", [0, 0, 1, 1])[1] / max(page.rect.height, 1)), min(1, raw.get("bbox", [0, 0, 1, 1])[2] / max(page.rect.width, 1)), min(1, raw.get("bbox", [0, 0, 1, 1])[3] / max(page.rect.height, 1))], bbox_raw=raw.get("bbox")))
            for index, image in enumerate(page.get_image_info(full=True), len(blocks) + 1):
                blocks.append(_block(number, index, "image", "", "native_pdf_image", .9, bbox_raw=image.get("bbox")))
            pages.append({"page": number, "width": page.rect.width, "height": page.rect.height, "blocks": blocks})
        pdf.close()
        return pages
    except Exception:
        try:
            from pypdf import PdfReader  # type: ignore
            reader = PdfReader(str(path))
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                blocks = [_block(number, 1, "text", text, "pypdf", .82)] if text.strip() else []
                pages.append({"page": number, "width": 0, "height": 0, "blocks": blocks})
            return pages
        except Exception as exc:
            raise RuntimeError(f"PDF fallback failed: {exc}") from exc



def _mineru_pdf(path: Path, root: Path) -> list[dict]:
    """Run the MinerU CLI and convert its middle JSON into pages."""
    executable = settings.file_processing_mineru_command
    resolved = shutil.which(executable) or (str(Path(sys.executable).with_name("mineru.exe")) if Path(sys.executable).with_name("mineru.exe").exists() else None)
    if not resolved:
        raise RuntimeError("MinerU command not found")
    out = root / "mineru"
    out.mkdir(parents=True, exist_ok=True)
    cmd = [resolved, "-p", str(path), "-o", str(out), "-m", "auto", "-b", "pipeline", "-f", "true", "-t", "true"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    (out / "mineru.log").write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "MinerU failed")[-4000:])
    middle = next(iter(out.rglob("*_middle.json")), None)
    if not middle:
        raise RuntimeError("MinerU did not produce middle JSON")
    raw = json.loads(middle.read_text(encoding="utf-8"))
    pages = []
    for number, page in enumerate(raw.get("pdf_info", raw.get("pages", [])), 1):
        blocks = []
        for index, item in enumerate(page.get("para_blocks", page.get("blocks", [])), 1):
            text = item.get("text") or item.get("content") or item.get("latex") or item.get("formula") or ""
            typ = str(item.get("type") or "text").lower()
            if "formula" in typ or "equation" in typ: typ = "formula"
            elif "table" in typ: typ = "table"
            elif "image" in typ or "figure" in typ: typ = "image"
            elif "title" in typ or "heading" in typ: typ = "heading"
            blocks.append(_block(number, index, typ, text, "mineru", float(item.get("confidence", .92)), item.get("bbox"), latex=item.get("latex") or item.get("formula")))
        pages.append({"page": number, "width": page.get("page_width", 0), "height": page.get("page_height", 0), "blocks": blocks})
    if not pages:
        raise RuntimeError("MinerU returned no pages")
    return pages



def _office_pages(path: Path) -> list[dict]:
    """Extract pages from PPTX, DOCX, XLSX/XLS or plain text."""
    ext = path.suffix.lower()
    pages: list[dict] = []
    if ext == ".pptx":
        from pptx import Presentation  # type: ignore
        for number, slide in enumerate(Presentation(str(path)).slides, 1):
            blocks = []
            for index, shape in enumerate(slide.shapes, 1):
                text = getattr(shape, "text", "") or ""
                if text.strip(): blocks.append(_block(number, index, "heading" if getattr(shape, "is_placeholder", False) and getattr(shape, "placeholder_format", None) else "text", text, "python-pptx", .96))
            pages.append({"page": number, "slide_number": number, "width": 0, "height": 0, "blocks": blocks, "title": next((b["text"] for b in blocks if b["type"] == "heading"), "")})
        return pages
    if ext == ".docx":
        from docx import Document  # type: ignore
        blocks = [_block(1, i, "heading" if paragraph.style.name.lower().startswith("heading") else "text", paragraph.text, "python-docx", .95) for i, paragraph in enumerate(Document(str(path)).paragraphs, 1) if paragraph.text.strip()]
        return [{"page": 1, "width": 0, "height": 0, "blocks": blocks}]
    if ext in {".xlsx", ".xls"}:
        from openpyxl import load_workbook  # type: ignore
        book = load_workbook(path, read_only=True, data_only=True)
        for number, sheet in enumerate(book.worksheets, 1):
            lines = [" | ".join(str(value or "") for value in row) for row in sheet.iter_rows(values_only=True)]
            text = "\n".join(line for line in lines if line.strip())
            pages.append({"page": number, "width": 0, "height": 0, "blocks": [_block(number, 1, "table", text, "openpyxl", .95)] if text else [], "sheet": sheet.title})
        return pages
    text = path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".json":
        try: text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except Exception: pass
    return [{"page": 1, "width": 0, "height": 0, "blocks": [_block(1, 1, "text", text, "text", .99)] if text.strip() else []}]



def _office_fallback(path: Path) -> list[dict]:
    """Extract readable XML text when an optional office parser is absent."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".xml") and any(token in name for token in ("document", "slide", "sheet", "sharedStrings"))]
            values: list[str] = []
            for name in names:
                try:
                    root = ET.fromstring(archive.read(name))
                    values.extend((node.text or "").strip() for node in root.iter() if node.text and node.text.strip())
                except Exception:
                    continue
            text = "\n".join(dict.fromkeys(values))
            return [{"page": 1, "width": 0, "height": 0, "blocks": [_block(1, 1, "text", text, "zip_xml_fallback", .55)] if text else []}]
    except Exception:
        return [{"page": 1, "width": 0, "height": 0, "blocks": []}]



def _pages_to_chunks(pages: list[dict], filename: str) -> list[dict]:
    """Flatten page blocks into retrieval chunks.

    The running ``section`` follows the last heading so each chunk keeps the
    outline context it appeared under.
    """
    chunks: list[dict] = []
    section = ""
    for page in pages:
        for block in page.get("blocks", []):
            content = (block.get("markdown") or block.get("text") or "").strip()
            if not content:
                continue
            if block.get("type") == "heading": section = content[:512]
            chunks.append({"page_number": page.get("page", 0), "section": section, "chunk_type": block.get("type", "text"), "content": content, "metadata": {"filename": filename, "block_id": block.get("id"), "bbox": block.get("bbox"), "bbox_raw": block.get("bbox_raw"), "confidence": block.get("confidence", 0), "source": block.get("source"), "slide_number": page.get("slide_number"), "sheet": page.get("sheet"), "latex": block.get("latex")}})
    return chunks

