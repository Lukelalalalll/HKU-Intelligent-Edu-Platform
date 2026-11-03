"""Course route package.

``common`` owns the router and the shared permission and serialization
helpers; ``catalog``, ``discussion`` and ``materials`` register their paths
on it through a wildcard import.
"""

from .common import router
from . import discussion, materials, catalog

__all__ = ["router"]
