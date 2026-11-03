from __future__ import annotations
import json, os, shutil
from pathlib import Path
from typing import Any

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def validate_manifest(root: Path, manifest: dict) -> None:
    for name in manifest.get("page_files", []):
        if not (root / name).is_file(): raise ValueError(f"missing artifact: {name}")
    for name in ("manifest.json", "document.md", "chunks.jsonl"):
        if not (root / name).is_file(): raise ValueError(f"missing artifact: {name}")

def atomic_publish(temp_root: Path, final_root: Path) -> None:
    final_root.parent.mkdir(parents=True, exist_ok=True)
    backup = final_root.with_name(final_root.name + ".old")
    if backup.exists(): shutil.rmtree(backup, ignore_errors=True)
    if final_root.exists(): os.replace(final_root, backup)
    try:
        os.replace(temp_root, final_root)
    except Exception:
        if backup.exists(): os.replace(backup, final_root)
        raise
    else:
        if backup.exists(): shutil.rmtree(backup, ignore_errors=True)
