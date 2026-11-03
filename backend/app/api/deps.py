"""Re-exported HTTP auth dependencies.

Routes import ``current_user`` and ``require_roles`` from here so the security
module can change without touching every route module.
"""

from app.core.security import current_user, require_roles

__all__ = ["current_user", "require_roles"]

