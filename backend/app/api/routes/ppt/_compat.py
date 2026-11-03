"""Compatibility route selection during the HTTP migration."""
from fastapi.routing import APIRoute
from app.api.ppt_legacy_impl import router as legacy_router

def selected_routes(predicate):
    """Return legacy routes whose path, minus the ``/api/ppt`` prefix, matches.

    Args:
        predicate: Callable applied to the prefix-stripped route path.

    Returns:
        The matching ``APIRoute`` objects owned by the legacy router.
    """
    selected = []
    for route in legacy_router.routes:
        if isinstance(route, APIRoute) and predicate(route.path.removeprefix("/api/ppt")):
            selected.append(route)
    return selected
