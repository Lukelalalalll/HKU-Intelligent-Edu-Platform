from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Chunk, Document
router=APIRouter(prefix='/api/v1/search',tags=['search'])
@router.get('')
def search(q:str='',document_id:int|None=None,page:int|None=None,type:str|None=None,top_k:int=20,db:Session=Depends(get_db)):
    query=db.query(Chunk)
    if q: query=query.filter(Chunk.content.ilike(f'%{q}%'))
    if document_id: query=query.filter_by(document_id=document_id)
    if page: query=query.filter_by(page=page)
    if type: query=query.filter_by(chunk_type=type)
    return [{'chunk_id':c.id,'document_id':c.document_id,'page':c.page,'slide_number':(c.metadata_json or {}).get('slide_number'),'section':c.section,'type':c.chunk_type,'content':c.content,'metadata':c.metadata_json,'confidence':(c.metadata_json or {}).get('confidence',1.0),'filename':(db.get(Document,c.document_id).filename if db.get(Document,c.document_id) else ''),'score':1.0} for c in query.limit(top_k).all()]
