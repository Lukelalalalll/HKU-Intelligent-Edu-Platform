"""Compatibility route selection during the HTTP migration."""
from fastapi.routing import APIRoute
from app.api.ppt_legacy_impl import router as legacy_router

def selected_routes(predicate):
    selected = []
    for route in legacy_router.routes:
        if isinstance(route, APIRoute) and predicate(route.path.removeprefix("/api/ppt")):
            selected.append(route)
    return selected
