import sys
from pathlib import Path

import pytest
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.core import security  # noqa: E402
from app.core.security import hash_password  # noqa: E402


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_db():
    db = Session()
    try: yield db
    finally: db.close()


@pytest.fixture(autouse=True)
def setup(monkeypatch, tmp_path):
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    security.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    monkeypatch.setattr("app.core.config.settings.upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr("app.core.config.settings.file_processing_dir", str(tmp_path / "processed"))
    with Session() as db:
        db.add(User(username="teacher", email="teacher@test", name="Teacher", password_hash=hash_password("123456"), role=UserRole.teacher)); db.commit()
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def test_upload_creates_document_and_job():
    from app.services.file_processing import upload_asset
    with Session() as db:
        user = db.query(User).first()
        asset, document, job = upload_asset(db, uploader_id=user.id, filename="notes.txt", mime_type="text/plain", content=b"hello retrieval")
        assert asset.original_name == "notes.txt" and document.status == "queued" and job.status == "queued"


def test_supported_extension_rejects_unknown():
    from app.services.file_processing import validate_upload
    with pytest.raises(ValueError): validate_upload("virus.exe", "application/octet-stream", 1)


def test_text_pages_to_chunks(tmp_path):
    from app.services.file_processing import _office_pages, _pages_to_chunks
    path = tmp_path / "notes.txt"; path.write_text("Heading\nbody", encoding="utf-8")
    pages = _office_pages(path); chunks = _pages_to_chunks(pages, path.name)
    assert pages and chunks and chunks[0]["page_number"] == 1
