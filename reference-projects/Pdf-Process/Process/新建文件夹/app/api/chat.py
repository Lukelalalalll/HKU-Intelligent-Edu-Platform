from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Conversation, Message
from ..services.retrieval import retrieve, context_text
from ..services.ai_provider import complete, stream as provider_stream, ProviderError, provider_config, redact_error
from ..config import settings

router = APIRouter(prefix='/api/v1/chat', tags=['chat'])

class ConversationIn(BaseModel):
    title: str = '新对话'
    document_ids: list[int] = Field(default_factory=list)

class MessageIn(BaseModel):
    content: str
    document_ids: list[int] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    include_images: bool = False
    full_summary: bool = False

def _conversation(c): return {'id': c.id, 'title': c.title, 'document_ids': c.selected_document_ids or [], 'created_at': c.created_at}

@router.post('/conversations')
def create_conversation(payload: ConversationIn, db: Session = Depends(get_db)):
    c = Conversation(title=payload.title, selected_document_ids=payload.document_ids); db.add(c); db.commit(); db.refresh(c); return _conversation(c)

@router.get('/conversations')
def list_conversations(db: Session = Depends(get_db)):
    return [_conversation(c) for c in db.query(Conversation).order_by(Conversation.updated_at.desc()).all()]

@router.get('/conversations/{conversation_id}/messages')
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id): raise HTTPException(404, 'Conversation not found')
    return [{'id': m.id, 'role': m.role, 'content': m.content, 'document_ids': m.selected_document_ids or [], 'metadata': m.metadata_json or [], 'created_at': m.created_at} for m in db.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.id).all()]

def _prompt(content, evidence, full_summary=False):
    mode = '完整总结模式：先列目录，再按章节总结，覆盖每页/每张幻灯片，分别列出公式、代码、表格、图表，并列出低置信度或未覆盖页面。' if full_summary else '普通问答模式：只使用相关证据。'
    return f'''你是文档证据助手。{mode}\n必须尽量引用 [文件名 p.12] 或 [文件名 slide 23]。不确定时明确说明，不要把推测当原文。公式使用合法 LaTeX，代码使用 fenced code block。\n\n证据：\n{context_text(evidence)}\n\n用户问题：{content}'''

def _save_user(db, cid, payload):
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, 'Conversation not found')
    ids = payload.document_ids or c.selected_document_ids or []
    c.selected_document_ids = ids; m = Message(conversation_id=cid, role='user', content=payload.content, selected_document_ids=ids); db.add(m); db.commit(); return c, ids

@router.post('/conversations/{conversation_id}/messages')
def add_message(conversation_id: int, payload: MessageIn, db: Session = Depends(get_db)):
    c, ids = _save_user(db, conversation_id, payload); evidence = retrieve(db, payload.content, ids, include_images=payload.include_images)
    try:
        answer = complete([{'role': 'user', 'content': _prompt(payload.content, evidence, payload.full_summary)}], provider=payload.provider, model=payload.model, api_key=payload.api_key, base_url=payload.base_url, temperature=payload.temperature, max_tokens=payload.max_tokens)
    except ProviderError as exc: raise HTTPException(503, str(exc))
    except Exception as exc: raise HTTPException(502, f'AI provider failed: {redact_error(exc)}')
    test_mode = (payload.provider or settings.ai_provider).lower() == 'mock'
    meta = {'evidence': evidence, 'test_mode': test_mode}; db.add(Message(conversation_id=conversation_id, role='assistant', content=answer, selected_document_ids=ids, metadata_json=meta)); db.commit()
    return {'role': 'assistant', 'content': answer, 'evidence': evidence, 'test_mode': test_mode}

@router.post('/conversations/{conversation_id}/stream')
def stream_message(conversation_id: int, payload: MessageIn, db: Session = Depends(get_db)):
    c, ids = _save_user(db, conversation_id, payload); evidence = retrieve(db, payload.content, ids, include_images=payload.include_images); prompt = _prompt(payload.content, evidence, payload.full_summary)
    try:
        provider_config(provider=payload.provider, model=payload.model, api_key=payload.api_key, base_url=payload.base_url, temperature=payload.temperature, max_tokens=payload.max_tokens)
    except ProviderError as exc:
        raise HTTPException(503, str(exc))
    def events():
        parts = []
        try:
            for token in provider_stream([{'role': 'user', 'content': prompt}], provider=payload.provider, model=payload.model, api_key=payload.api_key, base_url=payload.base_url, temperature=payload.temperature, max_tokens=payload.max_tokens):
                parts.append(token); yield f"data: {json.dumps({'type':'token','content':token}, ensure_ascii=False)}\n\n"
            answer = ''.join(parts); db.add(Message(conversation_id=conversation_id, role='assistant', content=answer, selected_document_ids=ids, metadata_json={'evidence': evidence, 'test_mode': False})); db.commit(); yield f"data: {json.dumps({'type':'done','evidence':evidence}, ensure_ascii=False)}\n\n"
        except ProviderError as exc:
            yield f"data: {json.dumps({'type':'error','status':503,'detail':str(exc)}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            if parts: yield f"data: {json.dumps({'type':'error','status':502,'detail':'stream failed after partial output'}, ensure_ascii=False)}\n\n"
            else:
                try:
                    answer = complete([{'role': 'user', 'content': prompt}], provider=payload.provider, model=payload.model, api_key=payload.api_key, base_url=payload.base_url, temperature=payload.temperature, max_tokens=payload.max_tokens)
                    db.add(Message(conversation_id=conversation_id, role='assistant', content=answer, selected_document_ids=ids, metadata_json={'evidence': evidence, 'fallback': True})); db.commit(); yield f"data: {json.dumps({'type':'fallback','content':answer,'evidence':evidence}, ensure_ascii=False)}\n\n"
                except Exception as fallback: yield f"data: {json.dumps({'type':'error','status':502,'detail':redact_error(fallback)}, ensure_ascii=False)}\n\n"
    return StreamingResponse(events(), media_type='text/event-stream')
