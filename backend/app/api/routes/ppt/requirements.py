"""Requirement interview, outline, message, source and checkpoint routes."""
from fastapi import APIRouter
from ._compat import selected_routes
router = APIRouter()
router.routes.extend(selected_routes(lambda p: "/requirements" in p or "/outline:generate" in p or "/messages" in p or "/sources" in p or "/checkpoints" in p))
