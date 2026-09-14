from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assignment, Course, Enrollment, FileContextBinding, FileProcessingChunk, FileProcessingDocument, FileAsset, Submission


def _terms(text: str) -> list[str]:
    return [item.casefold() for item in re.findall(r"[\w\u4e00-\u9fff]{2,}", text or "")]


def retrieve_chunks(db: Session, question: str, *, user_id: str, course_id: str | None = None, conversation_id: str | None = None, attachment_ids: list[str] | None = None, top_k: int = 8, include_images: bool = False) -> list[dict]:
    visible = []
    if course_id:
        enrolled = db.scalar(select(Enrollment.id).where(Enrollment.course_id == course_id, Enrollment.student_id == user_id))
        course = db.get(Course, course_id)
        if enrolled or (course and course.teacher_id == user_id):
            visible.extend(db.scalars(select(FileContextBinding.document_id).where(FileContextBinding.course_id == course_id, FileContextBinding.visibility == "course")).all())
            if course and course.teacher_id == user_id:
                visible.extend(db.scalars(select(FileContextBinding.document_id).join(Submission, Submission.id == FileContextBinding.target_id).join(Assignment, Assignment.id == Submission.assignment_id).where(FileContextBinding.target_type == "submission", Assignment.course_id == course_id)).all())
    else:
        # A student asking without an explicit course still gets material from
        # enrolled courses, while a teacher gets material from owned courses.
        course_ids = list(db.scalars(select(Enrollment.course_id).where(Enrollment.student_id == user_id)).all())
        course_ids.extend(db.scalars(select(Course.id).where(Course.teacher_id == user_id)).all())
        if course_ids:
            visible.extend(db.scalars(select(FileContextBinding.document_id).where(FileContextBinding.course_id.in_(list(dict.fromkeys(course_ids))), FileContextBinding.visibility == "course")).all())
    if conversation_id:
        conversation_docs = db.scalars(select(FileContextBinding.document_id).where(FileContextBinding.target_type == "conversation", FileContextBinding.target_id == conversation_id, FileContextBinding.owner_id == user_id)).all()
        if attachment_ids:
            attachment_hashes = db.scalars(select(FileAsset.sha256).where(FileAsset.id.in_(attachment_ids), FileAsset.uploader_id == user_id)).all()
            asset_docs = db.scalars(select(FileProcessingDocument.id).where(FileProcessingDocument.sha256.in_(attachment_hashes))).all()
            selected_docs = set(asset_docs) | set(db.scalars(select(FileProcessingDocument.id).where(FileProcessingDocument.id.in_(attachment_ids))).all())
            conversation_docs = [item for item in conversation_docs if item in selected_docs]
        visible.extend(conversation_docs)
    if not visible and not conversation_id and not course_id:
        visible.extend(db.scalars(select(FileContextBinding.document_id).where(FileContextBinding.owner_id == user_id)).all())
    visible = list(dict.fromkeys(visible))
    if not visible: return []
    rows = db.scalars(select(FileProcessingChunk).join(FileProcessingDocument).where(FileProcessingChunk.document_id.in_(visible), FileProcessingDocument.status.in_(["ready", "partial_ready"]))).all()
    terms = _terms(question)
    ranked = []
    for chunk in rows:
        content = (chunk.content or "").casefold()
        score = sum(content.count(term) for term in terms) if terms else 1
        if chunk.chunk_type == "image" and not include_images: continue
        ranked.append((score, chunk))
    ranked.sort(key=lambda item: (item[0], item[1].id), reverse=True)
    result = []
    for score, chunk in ranked[:top_k]:
        document = db.get(FileProcessingDocument, chunk.document_id); asset = db.get(FileAsset, document.file_asset_id) if document else None
        if not document: continue
        metadata = chunk.metadata_json or {}
        result.append({"document_id": document.id, "filename": document.filename, "file_asset_id": asset.id if asset else None, "page": chunk.page_number, "slide_number": metadata.get("slide_number"), "section": chunk.section, "chunk_id": chunk.id, "content": chunk.content, "chunk_type": chunk.chunk_type, "confidence": metadata.get("confidence", 1.0), "bbox": metadata.get("bbox"), "has_image": include_images and chunk.chunk_type in {"image", "formula", "table"}, "artifact_url": f"/api/file-processing/documents/{document.id}/artifacts/pages/page-{(chunk.page_number or 1):03d}.json", "score": score})
    return result


def context_text(evidence: list[dict], max_chars: int = 12000) -> str:
    parts, size = [], 0
    for item in evidence:
        marker = f"[{item['filename']} slide {item['slide_number']}]" if item.get("slide_number") else f"[{item['filename']} p.{item.get('page')} ]"
        value = f"{marker} section={item.get('section') or ''} confidence={item.get('confidence')}\n{item['content']}"
        if size + len(value) > max_chars: break
        parts.append(value); size += len(value)
    return "\n\n".join(parts)
