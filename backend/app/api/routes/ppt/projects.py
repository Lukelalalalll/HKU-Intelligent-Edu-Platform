from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: p in {"/projects", "/projects/{project_id}", "/themes", "/themes/{theme_id}/layouts", "/themes/{theme_id}/layouts/{layout_id}/preview.svg"}))
