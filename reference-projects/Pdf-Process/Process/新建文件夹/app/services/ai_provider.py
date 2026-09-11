from __future__ import annotations
import json
import httpx
from ..config import settings

class ProviderError(RuntimeError): pass

def redact_error(value):
    value = str(value or '')
    if settings.ai_api_key:
        value = value.replace(settings.ai_api_key, '[REDACTED]')
    return value[:500]

def provider_config(provider=None, model=None, temperature=None, max_tokens=None, api_key=None, base_url=None):
    p = (provider or settings.ai_provider or 'openai-compatible').lower()
    key = api_key or settings.ai_api_key
    if p != 'mock' and not key: raise ProviderError('AI_API_KEY is not configured')
    if p not in {'gemini', 'deepseek', 'openai-compatible', 'openai', 'mock'}: raise ProviderError(f'Unsupported AI provider: {p}')
    default_base = settings.ai_base_url
    if p == 'gemini' and (not base_url and default_base == 'https://api.openai.com/v1'):
        default_base = 'https://generativelanguage.googleapis.com'
    if p == 'deepseek' and (not base_url and default_base == 'https://api.openai.com/v1'):
        default_base = 'https://api.deepseek.com/v1'
    return {'provider': p, 'api_key': key, 'model': model or settings.ai_model, 'temperature': settings.ai_temperature if temperature is None else temperature, 'max_tokens': max_tokens or settings.ai_max_tokens, 'base_url': (base_url or default_base).rstrip('/')}

def _headers(cfg): return {'Authorization': f"Bearer {cfg['api_key']}", 'Content-Type': 'application/json'}

def complete(messages, **kwargs):
    cfg = provider_config(**kwargs)
    if cfg['provider'] == 'mock': return '[test_mode] Mock provider response. Evidence was received and no real model was called.'
    if cfg['provider'] == 'gemini':
        url = f"{cfg['base_url']}/v1beta/models/{cfg['model']}:generateContent?key={cfg['api_key']}"
        body = {'contents': [{'role': 'user' if m['role'] == 'user' else 'model', 'parts': [{'text': m['content']}]} for m in messages], 'generationConfig': {'temperature': cfg['temperature'], 'maxOutputTokens': cfg['max_tokens']}}
        response = httpx.post(url, json=body, timeout=120); response.raise_for_status(); data = response.json(); return data['candidates'][0]['content']['parts'][0]['text']
    url = cfg['base_url'] + '/chat/completions' if not cfg['base_url'].endswith('/chat/completions') else cfg['base_url']
    body = {'model': cfg['model'], 'messages': messages, 'temperature': cfg['temperature'], 'max_tokens': cfg['max_tokens']}
    response = httpx.post(url, headers=_headers(cfg), json=body, timeout=120); response.raise_for_status(); return response.json()['choices'][0]['message']['content']

def stream(messages, **kwargs):
    cfg = provider_config(**kwargs)
    if cfg['provider'] == 'mock':
        yield '[test_mode] Mock provider response. Evidence was received and no real model was called.'
        return
    if cfg['provider'] == 'gemini':
        # Gemini REST streaming is parsed as newline-delimited JSON when enabled.
        url = f"{cfg['base_url']}/v1beta/models/{cfg['model']}:streamGenerateContent?alt=sse&key={cfg['api_key']}"
        body = {'contents': [{'role': 'user' if m['role'] == 'user' else 'model', 'parts': [{'text': m['content']}]} for m in messages], 'generationConfig': {'temperature': cfg['temperature'], 'maxOutputTokens': cfg['max_tokens']}}
        with httpx.stream('POST', url, json=body, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith('data: '):
                    data = json.loads(line[6:]); parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', []); 
                    if parts and parts[0].get('text'): yield parts[0]['text']
        return
    url = cfg['base_url'] + '/chat/completions' if not cfg['base_url'].endswith('/chat/completions') else cfg['base_url']
    body = {'model': cfg['model'], 'messages': messages, 'temperature': cfg['temperature'], 'max_tokens': cfg['max_tokens'], 'stream': True}
    with httpx.stream('POST', url, headers=_headers(cfg), json=body, timeout=120) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith('data: '):
                payload = line[6:]
                if payload == '[DONE]': break
                try:
                    value = json.loads(payload).get('choices', [{}])[0].get('delta', {}).get('content')
                    if value: yield value
                except json.JSONDecodeError: continue
