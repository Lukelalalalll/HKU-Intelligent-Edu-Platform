"""Deck generation, visual research and page batch action routes."""
from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/design:generate" in p or "generation-jobs" in p or "visual-jobs" in p or p == "/projects/{project_id}/actions/batch" or p.endswith("/pages/{page_id}/actions")))
