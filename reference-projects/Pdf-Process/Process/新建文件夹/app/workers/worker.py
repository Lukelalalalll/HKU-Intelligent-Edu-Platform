import time
from ..db import SessionLocal
from ..models import ProcessingJob, Document
from ..services.pipeline import process_document
from ..config import settings
def run():
    while True:
        db=SessionLocal(); job=db.query(ProcessingJob).filter_by(status='queued').order_by(ProcessingJob.id).first()
        if job:
            doc=db.get(Document,job.document_id)
            try: process_document(db,doc,job)
            except Exception: pass
        db.close(); time.sleep(settings.worker_poll_seconds)
if __name__=='__main__': run()
