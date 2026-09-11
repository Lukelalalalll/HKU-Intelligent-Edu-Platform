from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas import CoursewareQueryIn, CoursewareQueryOut
from app.services.courseware_rag.service import courseware_rag

router = APIRouter(prefix="/api/courseware-agent", tags=["courseware-agent"])

@router.post("/query", response_model=CoursewareQueryOut)
def query(payload: CoursewareQueryIn, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    return courseware_rag(db, payload.question, user.id, payload.course_id)
