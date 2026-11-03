"""Compatibility export for the course route package.

The package ``app.api.routes.courses`` owns the router and its helpers; this
module only keeps the pre-split single-module import path importable.

Deprecated:
    Import ``app.api.routes.courses`` as a package; this module name is
    shadowed by the package directory and stays only for historical call sites.
"""
from app.api.routes.courses import router

__all__ = ["router"]
