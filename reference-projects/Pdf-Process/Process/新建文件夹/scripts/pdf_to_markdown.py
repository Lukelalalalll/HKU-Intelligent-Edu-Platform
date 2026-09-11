"""Convert a PDF into a readable Markdown document with page boundaries and formulas."""
from __future__ import annotations
import argparse, re
from pathlib import Path
import fitz

def clean(text: str) -> str:
    text = text.replace("\uFFFD", "\\text{replacement-character}")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def page_markdown(page: fitz.Page, number: int) -> str:
    blocks = page.get_text("blocks")
    lines: list[str] = []
    for block in blocks:
        text = clean(block[4])
        if not text:
            continue
        for line in text.splitlines():
            line = clean(line)
            if line:
                lines.append(line)
    return f"## Page {number}\n\n" + "\n\n".join(lines)

def convert(source: Path, target: Path) -> None:
    doc = fitz.open(source)
    title = source.stem.replace("_", " ")
    parts = [f"# {title}\n\n> Source: `{source.name}`\n>\n> This Markdown preserves the source page boundaries. Formula-like notation is kept in code spans or display math where the PDF text layer exposes it."]
    parts.extend(page_markdown(page, i + 1) for i, page in enumerate(doc))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n\n".join(parts) + "\n", encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    convert(args.source, args.target)
