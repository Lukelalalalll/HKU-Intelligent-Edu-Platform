"""Student courseware agent routes: RAG conversations and attachments.

Only students may call these endpoints, and a course-bound conversation
requires an enrolment in that course.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models import AgentConversation, AgentMessage, User, UserRole, Course, Enrollment
from app.schemas import AgentConversationCreate, AgentConversationDetail, AgentConversationOut, AgentMessageCreate, AgentMessageOut, CoursewareQueryIn, CoursewareQueryOut
from sqlalchemy import select
from app.services.courseware_rag.service import courseware_rag, unified_courseware_rag
from app.services.file_processing import upload_asset_stream, bind_document
from app.models import AgentMessageAttachment, FileProcessingDocument, FileAsset

router = APIRouter(prefix="/api/courseware-agent", tags=["courseware-agent"])

@router.get("/conversations", response_model=list[AgentConversationOut])
def list_conversations(user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """List the student's courseware conversations, newest first."""
    return db.scalars(select(AgentConversation).where(AgentConversation.user_id == user.id).order_by(AgentConversation.created_at.desc())).all()

@router.post("/conversations", response_model=AgentConversationOut, status_code=201)
def create_conversation(payload: AgentConversationCreate, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Create a conversation for a course the student is enrolled in."""
    if payload.course_id and not db.scalar(select(Enrollment.id).where(Enrollment.course_id == payload.course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    conversation = AgentConversation(user_id=user.id, title=payload.title.strip() or "新对话", course_id=payload.course_id)
    db.add(conversation); db.commit(); db.refresh(conversation); return conversation

@router.get("/conversations/{conversation_id}", response_model=AgentConversationDetail)
def get_conversation(conversation_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Return a conversation with its messages in creation order."""
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    messages = db.scalars(select(AgentMessage).where(AgentMessage.conversation_id == conversation.id).order_by(AgentMessage.created_at.asc())).all()
    return AgentConversationDetail.model_validate({"id": conversation.id, "title": conversation.title, "rag_mode": conversation.rag_mode, "created_at": conversation.created_at, "messages": [AgentMessageOut.model_validate(m) for m in messages]})

@router.post("/conversations/{conversation_id}/messages", response_model=AgentMessageOut, status_code=201)
def append_message(conversation_id: str, payload: AgentMessageCreate, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Append one message and bind uploaded attachments to it."""
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    message = AgentMessage(conversation_id=conversation.id, role=payload.role, content=payload.content, citations=payload.citations, model=payload.model)
    if payload.role == "user" and conversation.title == "新对话": conversation.title = payload.content[:32]
    db.add(message); db.flush()
    if payload.role == "user" and payload.attachment_ids:
        assets = db.scalars(select(FileAsset).where(FileAsset.id.in_(payload.attachment_ids), FileAsset.uploader_id == user.id)).all()
        documents = {item.sha256: item for item in db.scalars(select(FileProcessingDocument).where(FileProcessingDocument.sha256.in_(db.scalars(select(FileAsset.sha256).where(FileAsset.id.in_(payload.attachment_ids), FileAsset.uploader_id == user.id)).all()))).all()}
        for asset in assets:
            document = documents.get(asset.sha256)
            db.add(AgentMessageAttachment(message_id=message.id, file_asset_id=asset.id, document_id=document.id if document else None))
    db.commit(); db.refresh(message); return message

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Delete a conversation owned by the caller."""
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    db.delete(conversation); db.commit(); return {"message": "Conversation deleted"}

@router.post("/query", response_model=CoursewareQueryOut)
def query(payload: CoursewareQueryIn, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Answer a courseware question through the unified RAG pipeline.

    Raises:
        HTTPException: 403 when the student is not enrolled in the resolved
            course.
    """
    if payload.conversation_id:
        conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == payload.conversation_id, AgentConversation.user_id == user.id))
        if not conversation: raise HTTPException(404, "Conversation not found")
        payload.course_id = payload.course_id or conversation.course_id
    if payload.course_id and not db.scalar(select(Enrollment.id).where(Enrollment.course_id == payload.course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    return unified_courseware_rag(db, payload.question, user.id, payload.course_id, payload.conversation_id, payload.attachment_ids)


@router.post("/conversations/{conversation_id}/attachments", status_code=201)
def upload_attachment(conversation_id: str, file: UploadFile = File(...), user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    """Store a conversation attachment and start its processing job."""
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: raise HTTPException(404, "Conversation not found")
    try:
        asset, document, job = upload_asset_stream(db, uploader_id=user.id, filename=file.filename or "attachment", mime_type=file.content_type, file=file.file, target_type="conversation", target_id=conversation_id, owner_id=user.id, course_id=conversation.course_id, visibility="owner")
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    return {"id": asset.id, "name": asset.original_name, "document_id": document.id, "job_id": job.id if job else None, "processing_status": document.status}
