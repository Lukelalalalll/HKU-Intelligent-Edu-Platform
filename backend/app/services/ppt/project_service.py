"""Project domain facade over ``PptApplicationService``."""

from .services_base import PptServiceBase

class ProjectService(PptServiceBase):
    """Project lifecycle and shared PPT serialization operations."""
    def list(self): return self._app.list_projects()
    def create(self, title, request_text, course_id=None): return self._app.create_project(title, request_text, course_id)
    def get(self, project_id): return self._app.project(project_id)
    def patch(self, project_id, payload):
        """Apply a title and request-text edit, then serialize the project."""
        project = self._app.project(project_id)
        if payload.get("title") is not None: project.title = payload["title"].strip() or project.title
        if payload.get("request_text") is not None: project.request_text = payload["request_text"].strip()
        self.db.commit()
        return self._app.serialize_project(project)
    def delete(self, project_id): return self._app.delete_project(project_id)
    def serialize(self, project): return self._app.serialize_project(project)
