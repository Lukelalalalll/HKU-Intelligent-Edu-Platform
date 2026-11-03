"""Compatibility export for the split PPT route package.

The package ``app.api.routes.ppt`` is the real router owner; this module only
keeps the pre-split ``from app.api.routes.ppt import router`` import shape.

Deprecated:
    Import ``app.api.routes.ppt`` as a package; this module name is shadowed
    by the package directory and stays only for historical call sites.
"""
from .ppt import router
__all__ = ["router"]
