"""Keyless image retrieval with a deterministic keyword ranker and optional CLIP reranking."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

STOPWORDS = {"the", "and", "for", "with", "from", "this", "that", "page", "slide", "的", "和", "与", "及", "为", "课程", "页面"}
SYNONYMS = {"可持续": "sustainable sustainability", "生态": "ecology ecosystem", "人工智能": "ai artificial intelligence", "教学": "education teaching", "数据": "data analytics"}


def extract_keywords(section: str, title: str, bullets: Iterable[str] = (), role: str = "") -> list[str]:
    text = " ".join([section or "", title or "", *[str(x) for x in bullets], role or ""]).lower()
    tokens = re.findall(r"[a-z][a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", text)
    output: list[str] = []
    for token in tokens:
        if token in STOPWORDS or token in output:
            continue
        output.append(token)
        if token in SYNONYMS:
            output.extend(x for x in SYNONYMS[token].split() if x not in output)
    return output[:24]


def query_text(section: str, title: str, bullets: Iterable[str] = (), role: str = "") -> str:
    words = extract_keywords(section, title, bullets, role)
    return " ".join(words[:10])


def rank_candidates(candidates: list[dict[str, Any]], keywords: list[str], limit: int = 6) -> list[dict[str, Any]]:
    """Rank title/description matches; CLIP can be applied by the caller as a second pass."""
    terms = set(keywords)
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        key = str(item.get("image_url") or item.get("url") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        hits = sum(1 for term in terms if term in haystack)
        base = float(item.get("score") or 0)
        item = dict(item); item["score"] = round(min(0.99, base * 0.45 + min(1, hits / max(1, len(terms))) * 0.55), 4)
        ranked.append(item)
    return sorted(ranked, key=lambda x: float(x.get("score") or 0), reverse=True)[:limit]


def stable_asset_id(url: str) -> str:
    return "asset-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
