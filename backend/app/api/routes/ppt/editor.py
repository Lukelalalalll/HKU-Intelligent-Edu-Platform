from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/pages" in p or "/storyboard" in p or p.endswith("/layouts") or p.endswith("/theme") or p.endswith("/preview.svg")))
