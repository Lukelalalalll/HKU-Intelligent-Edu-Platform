"""Split PPT route package preserving the legacy HTTP contract."""
from fastapi import APIRouter
from . import projects, requirements, generation, editor, assets, events, exports
router = APIRouter()
# Each split module selects the legacy routes it serves.  De-duplicating by
# (path, methods) keeps the generated OpenAPI schema identical to the
# pre-split router even when two modules match the same path.
seen = set()
for _module in (projects, requirements, generation, editor, assets, events, exports):
    for _route in _module.router.routes:
        key = (getattr(_route, "path", ""), tuple(sorted(getattr(_route, "methods", ()))))
        if key not in seen:
            router.routes.append(_route); seen.add(key)
__all__ = ["router", "projects", "requirements", "generation", "editor", "assets", "events", "exports"]
