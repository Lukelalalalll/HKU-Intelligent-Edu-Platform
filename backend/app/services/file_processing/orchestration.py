from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import CourseMaterial, CourseMaterialIngestion, FileAsset, FileContextBinding, FileProcessingChunk, FileProcessingDocument, FileProcessingJob, FileProcessingPage
from app.services.file_processing.validation import SUPPORTED_EXTENSIONS, validate_upload
from app.services.file_processing.artifacts import write_json
from app.services.file_processing.parsers.utils import _pages_to_chunks

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _process(db: Session, document: FileProcessingDocument, job: FileProcessingJob) -> None:
    asset = db.get(FileAsset, document.file_asset_id) if document.file_asset_id else db.scalar(select(FileAsset).where(FileAsset.sha256 == document.sha256).order_by(FileAsset.created_at.asc()))
    if not asset:
        raise RuntimeError("原始文件不存在")
    source = settings.upload_path / asset.storage_key
    final_root = settings.file_processing_path / document.id
    temp_root = settings.file_processing_path / f".tmp-{document.id}-{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        (temp_root / "assets").mkdir(); (temp_root / "logs").mkdir()
        target = temp_root / f"source{document.extension}"; shutil.copy2(source, target)
        document.status = "processing"; job.status = "running"; job.stage = "extracting"; job.attempts += 1; job.started_at = now_utc(); db.commit()
        parsed = parse_document(target, temp_root, document.mime_type)
        pages, parser, fallback_error = parsed.pages, parsed.parser, parsed.fallback_error
        job.total_pages = len(pages); job.processed_pages = 0; db.commit()
        chunks = _pages_to_chunks(pages, document.filename)
        db.execute(delete(FileProcessingPage).where(FileProcessingPage.document_id == document.id)); db.execute(delete(FileProcessingChunk).where(FileProcessingChunk.document_id == document.id))
        for index, page in enumerate(pages, 1):
            write_json(temp_root / "pages" / f"page-{page['page']:03d}.json", page)
            db.add(FileProcessingPage(document_id=document.id, page_number=page["page"], width=page.get("width", 0), height=page.get("height", 0), payload=page))
            job.processed_pages = index; job.progress = round(index / max(len(pages), 1) * 90, 2); job.stage = "indexing"; db.commit()
        for index, chunk in enumerate(chunks):
            db.add(FileProcessingChunk(document_id=document.id, chunk_index=index, page_number=chunk["page_number"], section=chunk["section"], chunk_type=chunk["chunk_type"], content=chunk["content"], metadata_json=chunk["metadata"]))
        markdown = "\n\n".join(f"<!-- page: {page['page']} -->\n\n" + "\n\n".join(block.get("markdown") or block.get("text", "") for block in page.get("blocks", [])) for page in pages)
        (temp_root / "document.md").write_text(markdown, encoding="utf-8")
        (temp_root / "chunks.jsonl").write_text("".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks), encoding="utf-8")
        manifest = {"document_id": document.id, "filename": document.filename, "file_type": document.extension.lstrip("."), "sha256": document.sha256, "pages": len(pages), "successful_pages": len(pages), "failed_pages": 0, "source": parser, "parser": parser, "parser_version": parsed.parser_version, "fallback_error": fallback_error, "artifacts": [f"source{document.extension}", "document.md", "manifest.json", "chunks.jsonl"], "page_files": [f"pages/page-{page['page']:03d}.json" for page in pages], "stats": {"chunk_count": len(chunks), "block_count": sum(len(page.get("blocks", [])) for page in pages)}}
        write_json(temp_root / "manifest.json", manifest)
        from app.services.file_processing.artifacts import validate_manifest, atomic_publish
        validate_manifest(temp_root, manifest); atomic_publish(temp_root, final_root)
        document.page_count = len(pages); document.parser = parser; document.parser_version = parsed.parser_version; document.artifact_dir = str(final_root); document.manifest_json = manifest; document.error_message = fallback_error; document.status = "partial_ready" if fallback_error else "ready"
        job.stage = "ready"; job.progress = 100; job.processed_pages = len(pages); job.total_pages = len(pages); job.status = "completed"; job.finished_at = now_utc(); db.commit()
        material_ids = db.scalars(select(CourseMaterial.id).where(CourseMaterial.file_asset_id == document.file_asset_id)).all()
        for material_id in material_ids:
            ingestion = db.scalar(select(CourseMaterialIngestion).where(CourseMaterialIngestion.material_id == material_id))
            if ingestion:
                ingestion.status = document.status; ingestion.parser = parser; ingestion.error_message = fallback_error; ingestion.completed_at = now_utc()
        db.commit()
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def process_job(job_id: str) -> None:
    db = SessionLocal()
    retry = False
    try:
        job = db.get(FileProcessingJob, job_id)
        if not job: return
        document = db.get(FileProcessingDocument, job.document_id)
        if not document: return
        try:
            _process(db, document, job)
        except Exception as exc:
            db.rollback(); job = db.get(FileProcessingJob, job_id); document = db.get(FileProcessingDocument, job.document_id) if job else None
            if job and document:
                job.error_message = str(exc)[:4000]
                if job.attempts < job.max_attempts:
                    job.status = "queued"; job.stage = "retry_wait"; document.status = "queued"
                    retry = True
                else:
                    job.status = "failed"; document.status = "failed"; document.error_message = job.error_message; job.finished_at = now_utc()
                material_ids = db.scalars(select(CourseMaterial.id).where(CourseMaterial.file_asset_id == document.file_asset_id)).all() if document else []
                for material_id in material_ids:
                    ingestion = db.scalar(select(CourseMaterialIngestion).where(CourseMaterialIngestion.material_id == material_id))
                    if ingestion: ingestion.status = "failed"; ingestion.error_message = job.error_message
                db.commit()
    finally:
        db.close()
        if retry:
            enqueue_job(job_id)


def enqueue_job(job_id: str, db: Session | None = None) -> None:
    from app.jobs.manager import JobManager
    owns_session = db is None
    db = db or SessionLocal()
    try:
        JobManager(db).enqueue("file_processing", (job_id,), f"file-processing:{job_id}")
    finally:
        if owns_session: db.close()


def recover_jobs() -> None:
    db = SessionLocal()
    try:
        jobs = db.scalars(select(FileProcessingJob).where(FileProcessingJob.status.in_(["queued", "running"]))).all()
        job_ids = []
        for job in jobs:
            if job.status == "running": job.status = "queued"
            job_ids.append(job.id)
        db.commit()
        for job_id in job_ids: enqueue_job(job_id)
    finally: db.close()


def ensure_document_for_asset(db: Session, asset: FileAsset, *, target_type: str | None = None, target_id: str | None = None, owner_id: str | None = None, course_id: str | None = None, visibility: str = "owner", metadata: dict | None = None) -> tuple[FileProcessingDocument, FileProcessingJob]:
    # Processing is content-addressed. A second upload of the same bytes can
    # attach a new business binding to the already parsed document.
    document = db.scalar(select(FileProcessingDocument).where(FileProcessingDocument.sha256 == asset.sha256).order_by(FileProcessingDocument.created_at.asc()))
    if document is None:
        document = db.scalar(select(FileProcessingDocument).where(FileProcessingDocument.file_asset_id == asset.id))
    if not document:
        document = FileProcessingDocument(file_asset_id=asset.id, filename=asset.original_name, extension=asset.extension or Path(asset.original_name).suffix.lower(), mime_type=asset.mime_type, sha256=asset.sha256, artifact_dir="", parser="pending", parser_version=settings.file_processing_parser_version)
        db.add(document); db.flush()
    if target_type and target_id:
        binding = db.scalar(select(FileContextBinding).where(FileContextBinding.document_id == document.id, FileContextBinding.target_type == target_type, FileContextBinding.target_id == target_id))
        if not binding: db.add(FileContextBinding(document_id=document.id, target_type=target_type, target_id=target_id, owner_id=owner_id, course_id=course_id, visibility=visibility, metadata_json=metadata or {}))
    job = db.scalar(select(FileProcessingJob).where(FileProcessingJob.document_id == document.id, FileProcessingJob.status.in_(["queued", "running"])).order_by(FileProcessingJob.created_at.desc()).with_for_update())
    if not job and document.status not in {"ready", "partial_ready"}:
        job = FileProcessingJob(document_id=document.id); db.add(job); db.flush()
    if not job:
        job = db.scalar(select(FileProcessingJob).where(FileProcessingJob.document_id == document.id).order_by(FileProcessingJob.created_at.desc()))
    db.commit()
    if job and job.status == "queued": enqueue_job(job.id, db=db)
    return document, job


def upload_asset(db: Session, *, uploader_id: str, filename: str, mime_type: str | None, content: bytes, target_type: str | None = None, target_id: str | None = None, owner_id: str | None = None, course_id: str | None = None, visibility: str = "owner", metadata: dict | None = None) -> tuple[FileAsset, FileProcessingDocument, FileProcessingJob]:
    name, ext = validate_upload(filename, mime_type, len(content))
    digest = _sha256(content)
    asset = db.scalar(select(FileAsset).where(FileAsset.uploader_id == uploader_id, FileAsset.sha256 == digest, FileAsset.original_name == name))
    if not asset:
        from app.storage import LocalStorage
        key, size, digest = LocalStorage(settings.upload_path).save(name, content)
        asset = FileAsset(original_name=name, mime_type=mime_type or "application/octet-stream", extension=ext, size_bytes=size, sha256=digest, storage_key=key, uploader_id=uploader_id, course_id=course_id)
        db.add(asset); db.flush()
    document, job = ensure_document_for_asset(db, asset, target_type=target_type, target_id=target_id, owner_id=owner_id or uploader_id, course_id=course_id, visibility=visibility, metadata=metadata)
    return asset, document, job


def bind_document(db: Session, document_id: str, *, target_type: str, target_id: str, owner_id: str | None = None, course_id: str | None = None, visibility: str = "owner", metadata: dict | None = None) -> FileContextBinding:
    binding = db.scalar(select(FileContextBinding).where(FileContextBinding.document_id == document_id, FileContextBinding.target_type == target_type, FileContextBinding.target_id == target_id))
    if binding:
        if metadata:
            binding.metadata_json = {**(binding.metadata_json or {}), **metadata}
            db.commit()
        return binding
    binding = FileContextBinding(document_id=document_id, target_type=target_type, target_id=target_id, owner_id=owner_id, course_id=course_id, visibility=visibility, metadata_json=metadata or {})
    db.add(binding); db.commit(); db.refresh(binding); return binding


def parse_document(source: Path, output_dir: Path, mime_type: str | None = None):
    """Resolve and execute the registered parser for a source document."""
    from app.services.file_processing.parsers import default_registry
    parser = default_registry().resolve(source.suffix, mime_type)
    return parser.parse(source, output_dir)


def processing_root(document_id: str) -> Path:
    return settings.file_processing_path / document_id
