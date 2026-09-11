from __future__ import annotations
import re
from sqlalchemy.orm import Session
from ..models import Chunk, Document, Page
from ..config import settings

def retrieve(db: Session, question: str, document_ids=None, top_k=None, include_images=False):
    ids = [int(x) for x in (document_ids or [])]
    query = db.query(Chunk, Document).join(Document, Document.id == Chunk.document_id).filter(Document.status.in_(['ready', 'partial_ready']))
    if ids: query = query.filter(Chunk.document_id.in_(ids))
    rows = query.all(); terms = [x.lower() for x in re.findall(r'[\w\u4e00-\u9fff]{2,}', question or '')]
    ranked = []
    for chunk, doc in rows:
        content = chunk.content or ''; low = content.lower(); score = sum(low.count(t) for t in terms)
        if not terms: score = 1
        ranked.append((score, chunk, doc))
    ranked.sort(key=lambda x: (x[0], x[1].id), reverse=True)
    selected = ranked[:top_k or settings.retrieval_top_k]
    pages = {(c.document_id, c.page) for _, c, _ in selected}
    for doc_id, page in list(pages):
        for extra in db.query(Chunk).filter(Chunk.document_id == doc_id, Chunk.page.in_([page - 1, page + 1])).limit(4).all():
            if all(extra.id != c.id for _, c, _ in selected):
                d = db.get(Document, extra.document_id); selected.append((0, extra, d))
    result = []
    for score, chunk, doc in selected:
        meta = chunk.metadata_json or {}; slide = meta.get('slide_number') or (chunk.page if doc.file_type == 'pptx' else None)
        image = include_images and bool(meta.get('needs_visual_verification') or chunk.chunk_type in ('formula', 'code', 'table', 'image'))
        result.append({'filename': doc.filename, 'page': chunk.page, 'slide_number': slide, 'chunk_id': chunk.id, 'content': chunk.content, 'confidence': meta.get('confidence', 1.0), 'has_image': image, 'source_file': meta.get('source_file') or doc.filename, 'score': score})
    return result

def context_text(evidence, max_chars=None):
    limit = max_chars or settings.retrieval_context_chars; parts = []; size = 0
    for item in evidence:
        marker = f"[{item['filename']} slide {item['slide_number']}]" if item.get('slide_number') else f"[{item['filename']} p.{item['page']}]"
        value = f"{marker} chunk={item['chunk_id']} confidence={item['confidence']}\n{item['content']}"
        if size + len(value) > limit: break
        parts.append(value); size += len(value)
    return '\n\n'.join(parts)
