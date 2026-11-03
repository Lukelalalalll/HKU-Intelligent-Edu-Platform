"""PPTX export job routes."""
from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/exports" in p))
