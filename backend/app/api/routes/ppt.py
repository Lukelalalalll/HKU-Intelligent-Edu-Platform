"""Compatibility facade for the legacy PPT API.

New integrations should use :mod:`ppt_v2`; keeping this import path stable
allows the frontend to migrate independently of the internal route split.
"""

from app.api.routes.ppt_legacy import router

__all__ = ["router"]
