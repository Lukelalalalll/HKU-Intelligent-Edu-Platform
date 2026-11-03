"""Project asset upload and per-page file routes."""
from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/assets" in p or p.endswith("/files")))
