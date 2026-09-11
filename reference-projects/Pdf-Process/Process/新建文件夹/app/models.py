from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now(): return datetime.now(timezone.utc)
class Document(Base):
    __tablename__='documents'
    id: Mapped[int]=mapped_column(primary_key=True)
    filename: Mapped[str]=mapped_column(String(512))
    file_type: Mapped[str]=mapped_column(String(16), default='pdf')
    sha256: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    status: Mapped[str]=mapped_column(String(32), default='queued')
    pages: Mapped[int|None]=mapped_column(Integer, nullable=True)
    error: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)
class ProcessingJob(Base):
    __tablename__='processing_jobs'
    id: Mapped[int]=mapped_column(primary_key=True)
    document_id: Mapped[int]=mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    status: Mapped[str]=mapped_column(String(32), default='queued')
    stage: Mapped[str]=mapped_column(String(64), default='queued')
    progress: Mapped[float]=mapped_column(Float, default=0)
    processed_pages: Mapped[int]=mapped_column(Integer, default=0)
    total_pages: Mapped[int|None]=mapped_column(Integer, nullable=True)
    log: Mapped[str]=mapped_column(Text, default='')
    error: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
class Page(Base):
    __tablename__='pages'
    id: Mapped[int]=mapped_column(primary_key=True)
    document_id: Mapped[int]=mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    page_number: Mapped[int]=mapped_column(Integer)
    width: Mapped[float]=mapped_column(Float, default=0)
    height: Mapped[float]=mapped_column(Float, default=0)
    payload: Mapped[dict]=mapped_column(JSON)
class Chunk(Base):
    __tablename__='chunks'
    id: Mapped[int]=mapped_column(primary_key=True)
    document_id: Mapped[int]=mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    page: Mapped[int]=mapped_column(Integer)
    section: Mapped[str|None]=mapped_column(String(512), nullable=True)
    chunk_type: Mapped[str]=mapped_column(String(32), default='text')
    content: Mapped[str]=mapped_column(Text)
    metadata_json: Mapped[dict]=mapped_column(JSON, default=dict)

class Conversation(Base):
    __tablename__='conversations'
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(512), default='新对话')
    selected_document_ids: Mapped[list]=mapped_column(JSON, default=list)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Message(Base):
    __tablename__='messages'
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int]=mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), index=True)
    role: Mapped[str]=mapped_column(String(32))
    content: Mapped[str]=mapped_column(Text)
    selected_document_ids: Mapped[list]=mapped_column(JSON, default=list)
    metadata_json: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
