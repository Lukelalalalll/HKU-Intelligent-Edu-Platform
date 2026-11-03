"""Filesystem-backed storage used by uploads, avatars and lesson assets."""

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

class LocalStorage:
    """Store bytes under a generated key inside one root directory."""
    def __init__(self, root: Path):
        """Create the root directory when it does not exist yet."""
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> tuple[str, int, str]:
        """Write bytes under a UUID key.

        Returns:
            Tuple of stored key, byte size and sha256 digest.
        """
        suffix = Path(filename).suffix.lower()
        key = f"{uuid4().hex}{suffix}"
        (self.root / key).write_bytes(content)
        return key, len(content), sha256(content).hexdigest()

    def open(self, key: str):
        """Open a stored key for reading."""
        return (self.root / key).open("rb")

    def delete(self, key: str) -> None:
        """Delete a key when the file exists."""
        path = self.root / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        """Return the API URL that streams a stored key."""
        return f"/api/files/{key}"

