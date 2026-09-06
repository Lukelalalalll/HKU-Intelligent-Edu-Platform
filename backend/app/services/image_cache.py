from __future__ import annotations

import hashlib, ipaddress, socket
from pathlib import Path
from urllib.parse import urlparse

import httpx


def validate_public_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("仅允许 http/https 图片地址")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("禁止本机地址")
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            addr = ipaddress.ip_address(info[4][0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise ValueError("禁止内网地址")
    except socket.gaierror:
        raise ValueError("无法解析图片主机")
    return url


def download_image(url: str, root: Path, public_url: str, *, max_bytes: int = 8 * 1024 * 1024, timeout: float = 8) -> dict:
    validate_public_url(url)
    response = httpx.get(url, follow_redirects=True, timeout=timeout, headers={"User-Agent": "HKU-Courseware-Agent/1.0"})
    response.raise_for_status()
    content = response.content
    if len(content) > max_bytes:
        raise ValueError("图片超过大小限制")
    mime = (response.headers.get("content-type") or "").split(";", 1)[0].lower()
    if not mime.startswith("image/"):
        raise ValueError("响应不是图片")
    digest = hashlib.sha256(content).hexdigest()
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(mime, ".img")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{digest}{ext}"
    if not path.exists():
        path.write_bytes(content)
    return {"asset_path": str(path), "public_url": f"{public_url}/{path.name}", "src": f"{public_url}/{path.name}", "mime_type": mime, "bytes": len(content), "content_hash": digest, "status": "ready"}
