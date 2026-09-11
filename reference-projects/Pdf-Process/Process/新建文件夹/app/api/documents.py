import shutil, hashlib
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Document, ProcessingJob
from ..config import settings
router=APIRouter(prefix='/api/v1/documents',tags=['documents'])
@router.post('')
async def upload(files:list[UploadFile]=File(...), db:Session=Depends(get_db)):
    out=[]
    for f in files:
        suffix = Path(f.filename or '').suffix.lower()
        if suffix not in {'.pdf', '.pptx'}: raise HTTPException(400,'Only PDF and PPTX files are accepted')
        data=await f.read(); h=hashlib.sha256(data).hexdigest(); doc=db.query(Document).filter_by(sha256=h).first()
        if not doc:
            doc=Document(filename=f.filename,sha256=h,file_type=suffix.lstrip('.')); db.add(doc); db.commit(); db.refresh(doc)
            root=settings.documents_dir/str(doc.id); root.mkdir(parents=True); (root/f'source{suffix}').write_bytes(data)
        else:
            root=settings.documents_dir/str(doc.id); root.mkdir(parents=True, exist_ok=True)
            target=root/f'source{suffix}'
            if not target.exists(): target.write_bytes(data)
        job=ProcessingJob(document_id=doc.id); db.add(job); db.commit(); db.refresh(job); out.append({'document_id':doc.id,'job_id':job.id,'filename':doc.filename,'status':doc.status})
    return out
@router.get('')
def list_documents(db:Session=Depends(get_db), status:str|None=None):
    q=db.query(Document).order_by(Document.id.desc());
    if status:q=q.filter_by(status=status)
    return q.all()
@router.get('/{document_id}')
def get_document(document_id:int,db:Session=Depends(get_db)):
    d=db.get(Document,document_id)
    if not d: raise HTTPException(404,'Document not found')
    return d
@router.delete('/{document_id}')
def delete_document(document_id:int,db:Session=Depends(get_db)):
    d=db.get(Document,document_id)
    if not d: raise HTTPException(404,'Document not found')
    shutil.rmtree(settings.documents_dir/str(document_id),ignore_errors=True); db.delete(d); db.commit(); return {'ok':True}
@router.get('/{document_id}/artifacts/{name:path}')
def artifact(document_id:int,name:str):
    p=settings.documents_dir/str(document_id)/name
    if not p.is_file(): raise HTTPException(404,'Artifact not found')
    from fastapi.responses import FileResponse
    return FileResponse(p)
