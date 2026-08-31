from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AgentConversation, AgentMessage, Course, User, UserRole
from app.schemas import (
    AgentConversationCreate,
    AgentConversationDetail,
    AgentConversationOut,
    AgentMessageCreate,
    AgentMessageOut,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])


def owned_conversation(conversation_id: str, user: User, db: Session) -> AgentConversation:
    conversation = db.scalar(
        select(AgentConversation).where(
            AgentConversation.id == conversation_id,
            AgentConversation.user_id == user.id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations", response_model=list[AgentConversationOut])
def list_conversations(
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    latest_message_at = select(func.max(AgentMessage.created_at)).where(
        AgentMessage.conversation_id == AgentConversation.id,
    ).scalar_subquery()
    return db.scalars(
        select(AgentConversation)
        .where(AgentConversation.user_id == user.id)
        .order_by(func.coalesce(latest_message_at, AgentConversation.created_at).desc())
    ).all()


@router.post("/conversations", response_model=AgentConversationOut, status_code=201)
def create_conversation(
    payload: AgentConversationCreate,
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    if payload.course_id:
        course = db.get(Course, payload.course_id)
        if not course or course.teacher_id != user.id:
            raise HTTPException(status_code=404, detail="Course not found")
    conversation = AgentConversation(user_id=user.id, title=payload.title.strip(), course_id=payload.course_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=AgentConversationDetail)
def get_conversation(
    conversation_id: str,
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(conversation_id, user, db)
    messages = db.scalars(
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation.id)
        .order_by(AgentMessage.created_at.asc())
    ).all()
    return AgentConversationDetail(
        id=conversation.id,
        title=conversation.title,
        rag_mode=conversation.rag_mode,
        created_at=conversation.created_at,
        messages=[AgentMessageOut.model_validate(message) for message in messages],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=AgentMessageOut, status_code=201)
def append_message(
    conversation_id: str,
    payload: AgentMessageCreate,
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(conversation_id, user, db)
    message = AgentMessage(
        conversation_id=conversation.id,
        role=payload.role,
        content=payload.content,
        citations=payload.citations,
        model=payload.model,
    )
    if payload.role == "user" and conversation.title in {"新对话", "New conversation"}:
        conversation.title = payload.content.strip()[:32]
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    user: User = Depends(require_roles(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    conversation = owned_conversation(conversation_id, user, db)
    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted"}
