from __future__ import annotations

import base64
import hashlib
import json
import re
from functools import lru_cache
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AiBusinessBinding, AiProvider


BUSINESSES = {
    "teacher_ppt_agent": {"role": "teacher", "display_name": "教师 PPT Agent", "description": "PPT 对话、需求分析、课件生成与编辑"},
    "teacher_lesson_plan_agent": {"role": "teacher", "display_name": "教师学案 Agent", "description": "学案对话与学案生成"},
    "student_lecturer": {"role": "student", "display_name": "学生 AI 讲师", "description": "基于课程材料的 AI 讲师问答"},
}


def _cipher():
    try:
        from cryptography.fernet import Fernet
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode()).digest()))
    except ImportError:
        key = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        class LocalCipher:
            def encrypt(self, value: bytes) -> bytes:
                return base64.urlsafe_b64encode(bytes(v ^ key[i % len(key)] for i, v in enumerate(value)))
            def decrypt(self, value: bytes) -> bytes:
                raw = base64.urlsafe_b64decode(value)
                return bytes(v ^ key[i % len(key)] for i, v in enumerate(raw))
        return LocalCipher()


def encrypt_api_key(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_api_key(value: str) -> str:
    return _cipher().decrypt(value.encode()).decode() if value else ""


def mask_api_key(value: str) -> str:
    return f"{value[:4]}••••{value[-4:]}" if len(value) > 8 else ("••••••••" if value else "")


def _env_fallback() -> dict[str, Any]:
    return {"base_url": settings.llm_base_url, "api_key": settings.llm_api_key, "model": settings.llm_model, "timeout_seconds": 120, "provider_type": "deepseek" if "deepseek" in settings.llm_base_url.lower() else "openai", "capabilities": {"json": True, "stream": True, "web_search": "deepseek" in settings.llm_base_url.lower()}}


def ensure_ai_defaults(db: Session) -> None:
    """Create the initial platform provider and business catalog for dev installs."""
    fallback = _env_fallback()
    provider = db.scalar(select(AiProvider).where(AiProvider.name == "default"))
    if not provider:
        provider = AiProvider(name="default", provider_type=fallback["provider_type"], base_url=fallback["base_url"].rstrip("/"), api_key_encrypted=encrypt_api_key(fallback["api_key"]) if fallback["api_key"] else "", default_model=fallback["model"], timeout_seconds=fallback["timeout_seconds"], capabilities_json=fallback["capabilities"])
        db.add(provider); db.flush()
    for code, meta in BUSINESSES.items():
        binding = db.scalar(select(AiBusinessBinding).where(AiBusinessBinding.business_code == code))
        if not binding:
            db.add(AiBusinessBinding(business_code=code, role=meta["role"], display_name=meta["display_name"], description=meta["description"], provider_id=provider.id, model=provider.default_model, is_enabled=True))
    db.commit()


class AIGateway:
    """Resolve a business mapping and expose a provider-neutral model API."""

    def __init__(self, db: Session, business_code: str):
        self.db = db
        self.business_code = business_code
        self.binding = db.scalar(select(AiBusinessBinding).where(AiBusinessBinding.business_code == business_code, AiBusinessBinding.is_enabled.is_(True)))
        self.provider = self.binding.provider if self.binding and self.binding.provider and self.binding.provider.is_enabled else None
        fallback = _env_fallback()
        self.api_key = decrypt_api_key(self.provider.api_key_encrypted) if self.provider else ("" if self.binding else fallback["api_key"])
        self.base_url = self.provider.base_url if self.provider else fallback["base_url"]
        self.model = (self.binding.model if self.binding and self.binding.model else self.provider.default_model if self.provider else fallback["model"])
        self.timeout = int(self.binding.timeout_seconds if self.binding and self.binding.timeout_seconds else self.provider.timeout_seconds if self.provider else fallback["timeout_seconds"])
        self.provider_type = self.provider.provider_type if self.provider else fallback["provider_type"]
        self.capabilities = (self.provider.capabilities_json if self.provider else fallback["capabilities"]) or {}

    def _client(self):
        if not self.api_key:
            raise HTTPException(409, f"AI 业务 {self.business_code} 尚未配置可用 API Key")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise HTTPException(500, "后端缺少 openai 依赖，请重新安装 requirements.txt") from exc
        return _cached_client(self.api_key, self.base_url.rstrip("/"), self.timeout)

    def json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client().chat.completions.create(model=self.model, temperature=0.2, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        text = response.choices[0].message.content or "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                raise HTTPException(502, "模型返回的结构不是有效 JSON") from exc
            return json.loads(match.group(0))

    def text(self, system: str, payload: dict[str, Any]) -> str:
        response = self._client().chat.completions.create(model=self.model, temperature=0.3, messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        return response.choices[0].message.content or ""

    def stream_json(self, system: str, payload: dict[str, Any]):
        response = self._client().chat.completions.create(model=self.model, temperature=0.2, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], stream=True)
        raw = ""
        emitted = ""
        for item in response:
            delta = getattr(item.choices[0].delta, "content", None) if getattr(item, "choices", None) else None
            if not delta:
                continue
            raw += delta
            marker = '"assistant_markdown"'
            start = raw.find(marker)
            if start >= 0:
                colon = raw.find(":", start + len(marker))
                encoded = raw[colon + 1:].lstrip() if colon >= 0 else ""
                if encoded.startswith('"'):
                    try:
                        decoded = json.loads(encoded[:encoded.find('"', 1) + 1])
                        if decoded.startswith(emitted):
                            chunk = decoded[len(emitted):]; emitted = decoded
                            if chunk: yield {"type": "chunk", "chunk": chunk}
                    except (ValueError, json.JSONDecodeError):
                        pass
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                raise HTTPException(502, "模型返回的结构不是有效 JSON") from exc
            data = json.loads(match.group(0))
        yield {"type": "final", "data": data}

    def chat(self, system: str, user: str) -> str:
        response = self._client().chat.completions.create(model=self.model, temperature=0.2, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return response.choices[0].message.content or ""

    def web_search_json(self, query: str, image_focus: bool = False) -> dict[str, Any]:
        if not self.capabilities.get("web_search"):
            raise HTTPException(409, f"当前 Provider 不支持 {self.business_code} 的联网搜索能力")
        response = self._client().responses.create(model=self.model, instructions="只输出 JSON：{results:[{title,image_url,url,snippet,license,score}]}。", input=query, tools=[{"type": "web_search"}], tool_choice={"type": "web_search"}, text={"format": {"type": "json_object"}}, max_output_tokens=1800)
        text = str(getattr(response, "output_text", "") or "")
        try:
            return json.loads(text or "{}")
        except json.JSONDecodeError as exc:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match: raise HTTPException(502, "联网搜索返回的结构不是有效 JSON") from exc
            return json.loads(match.group(0))


@lru_cache(maxsize=32)
def _cached_client(api_key: str, base_url: str, timeout: int):
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def gateway_for(db: Session, business_code: str) -> AIGateway:
    if business_code not in BUSINESSES:
        raise HTTPException(404, "未知 AI 业务")
    return AIGateway(db, business_code)
