from .common import *  # noqa: F401,F403

@router.get("/{course_id}/materials", response_model=list[CourseChapterOut])

def list_materials(course_id: str, kind: str = Query(..., pattern="^(lecture|tutorial)$"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    return [_chapter_out(chapter, db) for chapter in sorted((item for item in course.chapters if item.kind == kind), key=lambda item: item.sort_order)]


@router.post("/{course_id}/materials/chapters", response_model=CourseChapterOut, status_code=201)
def create_material_chapter(course_id: str, payload: CourseChapterCreate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    title = payload.title.strip()
    if any(item.kind == payload.kind and item.title.casefold() == title.casefold() for item in course.chapters):
        raise HTTPException(409, "Chapter title already exists")
    chapter = CourseChapter(course_id=course.id, kind=payload.kind, title=title, sort_order=len([item for item in course.chapters if item.kind == payload.kind]))
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter, db)


@router.patch("/{course_id}/materials/chapters/{chapter_id}", response_model=CourseChapterOut)
def update_material_chapter(course_id: str, chapter_id: str, payload: CourseChapterUpdate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    if payload.title is not None:
        title = payload.title.strip()
        if any(item.id != chapter.id and item.kind == chapter.kind and item.title.casefold() == title.casefold() for item in course.chapters):
            raise HTTPException(409, "Chapter title already exists")
        chapter.title = title
    _normalize_chapter_order(course, chapter.kind, chapter, payload.sort_order)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter, db)


@router.delete("/{course_id}/materials/chapters/{chapter_id}")
def delete_material_chapter(course_id: str, chapter_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    chapter_kind = chapter.kind
    chapter_id_value = chapter.id
    materials = list(chapter.materials)
    keys = [material.file_asset.storage_key for material in materials]
    for material in materials:
        db.delete(material)
        if material.file_asset:
            db.delete(material.file_asset)
    db.delete(chapter)
    db.commit()
    storage = LocalStorage(settings.upload_path)
    for key in keys:
        storage.delete(key)
    remaining = sorted((item for item in course.chapters if item.id != chapter_id_value and item.kind == chapter_kind), key=lambda item: (item.sort_order, item.created_at, item.id))
    for index, item in enumerate(remaining):
        item.sort_order = index
    db.commit()
    return {"message": "Chapter deleted"}


@router.post("/{course_id}/materials/chapters/{chapter_id}/files", response_model=CourseMaterialOut, status_code=201)
def upload_material(course_id: str, chapter_id: str, file: UploadFile = File(...), title: str | None = Form(default=None), user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    content = file.file.read()
    try:
        asset, document, job = upload_asset(db, uploader_id=user.id, filename=file.filename or "material", mime_type=file.content_type, content=content, owner_id=user.id, course_id=course.id, visibility="course")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    asset.course_id = course.id
    material = CourseMaterial(chapter=chapter, file_asset=asset, title=(title or file.filename or "Material").strip() or "Material", uploaded_by=user.id)
    db.add(material)
    db.commit()
    db.refresh(material)
    bind_document(db, document.id, target_type="course_material", target_id=material.id, owner_id=user.id, course_id=course.id, visibility="course")
    db.refresh(document)
    db.add(CourseMaterialIngestion(material_id=material.id, status=document.status, parser=document.parser, error_message=document.error_message)); db.commit()
    return _material_out(material, db)

@router.get("/{course_id}/materials/{material_id}/status")
def material_status(course_id: str, material_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    material = next((m for ch in course.chapters for m in ch.materials if m.id == material_id), None)
    if not material: raise HTTPException(404, "Material not found")
    document = db.scalar(select(FileProcessingDocument).where((FileProcessingDocument.file_asset_id == material.file_asset_id) | (FileProcessingDocument.sha256 == material.file_asset.sha256)))
    job = db.scalar(select(FileProcessingJob).where(FileProcessingJob.document_id == document.id).order_by(FileProcessingJob.created_at.desc())) if document else None
    return {"material_id": material_id, "document_id": document.id if document else None, "job_id": job.id if job else None, "status": document.status if document else "pending", "processing_status": document.status if document else "pending", "parser": document.parser if document else None, "error_message": document.error_message if document else None, "progress": job.progress if job else 0}

@router.post("/{course_id}/materials/assets", response_model=CourseMaterialOut, status_code=201)
def attach_material_asset(course_id: str, file_asset_id: str, kind: str = Query(..., pattern="^(lecture|tutorial)$"), chapter_id: str | None = None, chapter_title: str | None = None, title: str | None = None, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    if chapter_id:
        chapter = _chapter_or_404(course, chapter_id)
        if chapter.kind != kind: raise HTTPException(400, "Chapter kind mismatch")
    else:
        name = (chapter_title or "").strip()
        if not name or len(name) > 200: raise HTTPException(400, "请输入 chapter 名称")
        chapter = next((x for x in course.chapters if x.kind == kind and x.title.casefold() == name.casefold()), None)
        if not chapter:
            chapter = CourseChapter(course_id=course.id, kind=kind, title=name, sort_order=len([x for x in course.chapters if x.kind == kind])); db.add(chapter)
    asset = db.get(FileAsset, file_asset_id)
    if not asset or asset.uploader_id != user.id: raise HTTPException(404, "File asset not found")
    if db.scalar(select(CourseMaterial).where(CourseMaterial.file_asset_id == asset.id)): raise HTTPException(409, "File already attached")
    asset.course_id = course.id
    material = CourseMaterial(chapter=chapter, file_asset=asset, title=(title or asset.original_name).strip(), uploaded_by=user.id)
    db.add(material); db.flush(); document = db.scalar(select(FileProcessingDocument).where((FileProcessingDocument.file_asset_id == asset.id) | (FileProcessingDocument.sha256 == asset.sha256))); db.refresh(document) if document else None; db.add(CourseMaterialIngestion(material_id=material.id, status=document.status if document else "queued", parser=document.parser if document else "pending", error_message=document.error_message if document else None)); db.commit(); db.refresh(material)
    if document:
        bind_document(db, document.id, target_type="course_material", target_id=material.id, owner_id=user.id, course_id=course.id, visibility="course")
    return _material_out(material, db)

@router.post("/{course_id}/materials/{material_id}/reindex")
def reindex_material(course_id: str, material_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    material = next((m for ch in course.chapters for m in ch.materials if m.id == material_id), None)
    if not material: raise HTTPException(404, "Material not found")
    document, job = ensure_document_for_asset(db, material.file_asset, target_type="course_material", target_id=material.id, owner_id=user.id, course_id=course_id, visibility="course")
    document.status = "queued"
    if job is None:
        job = FileProcessingJob(document_id=document.id)
        db.add(job)
        db.flush()
    if job:
        job.status = "queued"; job.stage = "queued"; job.progress = 0; job.attempts = 0; job.error_message = None
        db.commit(); enqueue_job(job.id)
    return {"material_id": material_id, "document_id": document.id, "job_id": job.id if job else None, "status": "queued"}


@router.delete("/{course_id}/materials/{material_id}")
def delete_material(course_id: str, material_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    material = next((item for chapter in course.chapters for item in chapter.materials if item.id == material_id), None)
    if not material:
        raise HTTPException(404, "Material not found")
    key = material.file_asset.storage_key
    asset = material.file_asset
    db.delete(material)
    db.delete(asset)
    db.commit()
    LocalStorage(settings.upload_path).delete(key)
    return {"message": "Material deleted"}


@router.get("/{course_id}/materials/{material_id}/download")
def download_material(course_id: str, material_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    material = next((item for chapter in course.chapters for item in chapter.materials if item.id == material_id), None)
    if not material:
        raise HTTPException(404, "Material not found")
    path = settings.upload_path / material.file_asset.storage_key
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path, media_type=material.file_asset.mime_type, filename=material.file_asset.original_name)

