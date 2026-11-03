"""Shared dependency boundary for PPT application services."""
from sqlalchemy.orm import Session
from app.models import User
from .agent_service import PptApplicationService

class PptServiceBase:
    """Shared dependency boundary for PPT application services.

    Routes depend on this facade instead of the historical monolith, so a
    route module can be split without changing request handling.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self._app = PptApplicationService(db, user)

    def __getattr__(self, name):
        # Fall back to the composed application service so callers written
        # against the pre-split module keep resolving the mixin methods.
        return getattr(self._app, name)


class PptRouteService(PptServiceBase):
    """HTTP compatibility facade composed from the domain services.

    It keeps the old response behavior while ensuring routes depend on the
    application boundary rather than the historical service module.
    """
    def __init__(self, db: Session, user: User):
        super().__init__(db, user)
        from .project_service import ProjectService
        from .requirement_service import RequirementService
        from .generation_service import GenerationService
        from .editor_service import EditorService
        from .export_service import ExportService
        self.projects = ProjectService(db, user)
        self.requirements_service = RequirementService(db, user)
        self.generation = GenerationService(db, user)
        self.editor = EditorService(db, user)
        self.exports = ExportService(db, user)
