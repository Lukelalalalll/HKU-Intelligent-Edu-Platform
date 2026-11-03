from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/events/stream" in p or p.endswith("/messages/stream") or p.endswith("/requirements/chat/stream")))
