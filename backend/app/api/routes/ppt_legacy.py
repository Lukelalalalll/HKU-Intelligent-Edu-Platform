"""Deprecated compatibility import for the legacy PPT HTTP contract.

Kept for call sites written before the PPT routes were split into a package.

Deprecated:
    Import ``app.api.routes.ppt`` directly; that package selects the routes
    from the legacy router and owns the mounted ``router`` object.
"""
from .ppt import router
__all__ = ["router"]
