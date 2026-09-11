from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models import AgentConversation, AgentMessage, User, UserRole
from app.schemas import AgentConversationCreate, AgentConversationDetail, AgentConversationOut, AgentMessageCreate, AgentMessageOut, CoursewareQueryIn, CoursewareQueryOut
from sqlalchemy import select
from app.services.courseware_rag.service import courseware_rag

router = APIRouter(prefix="/api/courseware-agent", tags=["courseware-agent"])

@router.get("/conversations", response_model=list[AgentConversationOut])
def list_conversations(user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    return db.scalars(select(AgentConversation).where(AgentConversation.user_id == user.id).order_by(AgentConversation.created_at.desc())).all()

@router.post("/conversations", response_model=AgentConversationOut, status_code=201)
def create_conversation(payload: AgentConversationCreate, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    conversation = AgentConversation(user_id=user.id, title=payload.title.strip() or "新对话", course_id=payload.course_id)
    db.add(conversation); db.commit(); db.refresh(conversation); return conversation

@router.get("/conversations/{conversation_id}", response_model=AgentConversationDetail)
def get_conversation(conversation_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    messages = db.scalars(select(AgentMessage).where(AgentMessage.conversation_id == conversation.id).order_by(AgentMessage.created_at.asc())).all()
    return AgentConversationDetail.model_validate({"id": conversation.id, "title": conversation.title, "rag_mode": conversation.rag_mode, "created_at": conversation.created_at, "messages": [AgentMessageOut.model_validate(m) for m in messages]})

@router.post("/conversations/{conversation_id}/messages", response_model=AgentMessageOut, status_code=201)
def append_message(conversation_id: str, payload: AgentMessageCreate, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    message = AgentMessage(conversation_id=conversation.id, role=payload.role, content=payload.content, citations=payload.citations, model=payload.model)
    if payload.role == "user" and conversation.title == "新对话": conversation.title = payload.content[:32]
    db.add(message); db.commit(); db.refresh(message); return message

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    conversation = db.scalar(select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id))
    if not conversation: from fastapi import HTTPException; raise HTTPException(404, "Conversation not found")
    db.delete(conversation); db.commit(); return {"message": "Conversation deleted"}

@router.post("/query", response_model=CoursewareQueryOut)
def query(payload: CoursewareQueryIn, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    return courseware_rag(db, payload.question, user.id, payload.course_id)
