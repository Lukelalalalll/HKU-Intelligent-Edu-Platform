from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass
engine=create_engine(f"sqlite:///{(settings.data_dir/'process.db').resolve()}", connect_args={"check_same_thread":False})
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)

def ensure_schema():
    Base.metadata.create_all(engine)
    # Keep the single-file local database compatible with databases created by
    # the first MVP, without requiring Alembic for a desktop installation.
    if not inspect(engine).has_table('documents'):
        return
    migrations = {
        'documents': {
            'file_type': "ALTER TABLE documents ADD COLUMN file_type VARCHAR(16) DEFAULT 'pdf'",
        },
        'processing_jobs': {},
    }
    with engine.begin() as conn:
        for table, statements in migrations.items():
            columns = {c['name'] for c in inspect(engine).get_columns(table)}
            for column, statement in statements.items():
                if column not in columns:
                    conn.execute(text(statement))

ensure_schema()

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
