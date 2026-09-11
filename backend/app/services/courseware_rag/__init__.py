"""HKU Courseware RAG runtime facade."""
from .service import courseware_rag, ingest_material, query_courses

__all__ = ["courseware_rag", "ingest_material", "query_courses"]
