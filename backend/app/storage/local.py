from hashlib import sha256
from pathlib import Path
from uuid import uuid4

class LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> tuple[str, int, str]:
        suffix = Path(filename).suffix.lower()
        key = f"{uuid4().hex}{suffix}"
        (self.root / key).write_bytes(content)
        return key, len(content), sha256(content).hexdigest()

    def open(self, key: str):
        return (self.root / key).open("rb")

    def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        return f"/api/files/{key}"

