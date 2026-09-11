from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import ProcessingJob
router=APIRouter(prefix='/api/v1/jobs',tags=['jobs'])
@router.get('/{job_id}')
def get_job(job_id:int,db:Session=Depends(get_db)):
    j=db.get(ProcessingJob,job_id)
    if not j: raise HTTPException(404,'Job not found')
    return j
