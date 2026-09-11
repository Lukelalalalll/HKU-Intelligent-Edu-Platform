from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AiBusinessBinding, AiProvider, AuditLog, User, UserRole
from app.services.ai_gateway import BUSINESSES, decrypt_api_key, encrypt_api_key, gateway_for, mask_api_key

router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])
admin = Depends(require_roles(UserRole.admin))


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = Field(pattern="^(openai|deepseek)$")
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    default_model: str = Field(min_length=1, max_length=160)
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    capabilities: dict = Field(default_factory=dict)
    is_enabled: bool = True


class BusinessIn(BaseModel):
    provider_id: str | None = None
    model: str = Field(default="", max_length=160)
    embedding_model: str = Field(default="", max_length=160)
    timeout_seconds: int | None = Field(default=None, ge=10, le=600)
    is_enabled: bool = True


def audit(db: Session, user: User, action: str, resource_type: str, resource_id: str | None, details: dict | None = None):
    db.add(AuditLog(user_id=user.id, action=action, resource_type=resource_type, resource_id=resource_id, details=details or {}))


def provider_out(provider: AiProvider) -> dict:
    key = decrypt_api_key(provider.api_key_encrypted)
    return {"id": provider.id, "name": provider.name, "provider_type": provider.provider_type, "base_url": provider.base_url, "api_key_configured": bool(key), "api_key_masked": mask_api_key(key), "default_model": provider.default_model, "timeout_seconds": provider.timeout_seconds, "capabilities": provider.capabilities_json or {}, "is_enabled": provider.is_enabled, "updated_at": provider.updated_at.isoformat() if provider.updated_at else None}


@router.get("/providers")
def list_providers(user: User = admin, db: Session = Depends(get_db)):
    return {"items": [provider_out(p) for p in db.scalars(select(AiProvider).order_by(AiProvider.name)).all()]}


@router.post("/providers", status_code=201)
def create_provider(payload: ProviderIn, user: User = admin, db: Session = Depends(get_db)):
    if db.scalar(select(AiProvider).where(AiProvider.name == payload.name.strip())):
        raise HTTPException(409, "Provider 名称已存在")
    provider = AiProvider(name=payload.name.strip(), provider_type=payload.provider_type, base_url=payload.base_url.rstrip("/"), default_model=payload.default_model, timeout_seconds=payload.timeout_seconds, capabilities_json=payload.capabilities, is_enabled=payload.is_enabled)
    if payload.api_key: provider.api_key_encrypted = encrypt_api_key(payload.api_key)
    db.add(provider); db.flush(); audit(db, user, "ai.provider.created", "ai_provider", provider.id, {"name": provider.name, "provider_type": provider.provider_type}); db.commit(); db.refresh(provider)
    return provider_out(provider)


@router.patch("/providers/{provider_id}")
def update_provider(provider_id: str, payload: ProviderIn, user: User = admin, db: Session = Depends(get_db)):
    provider = db.get(AiProvider, provider_id)
    if not provider: raise HTTPException(404, "Provider 不存在")
    duplicate = db.scalar(select(AiProvider).where(AiProvider.name == payload.name.strip(), AiProvider.id != provider_id))
    if duplicate: raise HTTPException(409, "Provider 名称已存在")
    provider.name, provider.provider_type, provider.base_url, provider.default_model = payload.name.strip(), payload.provider_type, payload.base_url.rstrip("/"), payload.default_model
    provider.timeout_seconds, provider.capabilities_json, provider.is_enabled = payload.timeout_seconds, payload.capabilities, payload.is_enabled
    if payload.api_key: provider.api_key_encrypted = encrypt_api_key(payload.api_key)
    audit(db, user, "ai.provider.updated", "ai_provider", provider.id, {"name": provider.name}); db.commit(); db.refresh(provider)
    return provider_out(provider)


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str, user: User = admin, db: Session = Depends(get_db)):
    provider = db.get(AiProvider, provider_id)
    if not provider: raise HTTPException(404, "Provider 不存在")
    if db.scalar(select(AiBusinessBinding).where(AiBusinessBinding.provider_id == provider_id)):
        raise HTTPException(409, "Provider 仍被业务映射使用，请先解除映射")
    db.delete(provider); audit(db, user, "ai.provider.deleted", "ai_provider", provider_id); db.commit(); return {"ok": True}


@router.post("/providers/{provider_id}/test")
def test_provider(provider_id: str, user: User = admin, db: Session = Depends(get_db)):
    provider = db.get(AiProvider, provider_id)
    if not provider: raise HTTPException(404, "Provider 不存在")
    # Use a temporary binding-free probe while preserving the configured provider.
    key = decrypt_api_key(provider.api_key_encrypted)
    if not key: raise HTTPException(409, "Provider 尚未配置 API Key")
    from app.services.ai_gateway import _cached_client
    try:
        _cached_client(key, provider.base_url.rstrip("/"), provider.timeout_seconds).chat.completions.create(model=provider.default_model, messages=[{"role": "user", "content": "Reply with OK"}], max_tokens=8)
    except Exception as exc:
        raise HTTPException(502, f"Provider 连接失败：{exc}") from exc
    audit(db, user, "ai.provider.tested", "ai_provider", provider.id); db.commit(); return {"ok": True}


@router.get("/businesses")
def list_businesses(user: User = admin, db: Session = Depends(get_db)):
    rows = {row.business_code: row for row in db.scalars(select(AiBusinessBinding)).all()}
    items = []
    for code, meta in BUSINESSES.items():
        row = rows.get(code)
        items.append({"business_code": code, **meta, "provider_id": row.provider_id if row else None, "provider_name": row.provider.name if row and row.provider else None, "model": row.model if row else "", "embedding_model": row.embedding_model if row else "", "timeout_seconds": row.timeout_seconds if row else None, "is_enabled": row.is_enabled if row else False})
    return {"items": items}


@router.patch("/businesses/{business_code}")
def update_business(business_code: str, payload: BusinessIn, user: User = admin, db: Session = Depends(get_db)):
    meta = BUSINESSES.get(business_code)
    if not meta: raise HTTPException(404, "未知 AI 业务")
    if payload.provider_id and not db.get(AiProvider, payload.provider_id): raise HTTPException(404, "Provider 不存在")
    row = db.scalar(select(AiBusinessBinding).where(AiBusinessBinding.business_code == business_code))
    if not row:
        row = AiBusinessBinding(business_code=business_code, role=meta["role"], display_name=meta["display_name"], description=meta["description"]); db.add(row)
    row.provider_id, row.model, row.embedding_model, row.timeout_seconds, row.is_enabled = payload.provider_id, payload.model, payload.embedding_model, payload.timeout_seconds, payload.is_enabled
    audit(db, user, "ai.business.updated", "ai_business_binding", row.id, {"business_code": business_code, "provider_id": payload.provider_id, "model": payload.model}); db.commit(); return {"ok": True}
