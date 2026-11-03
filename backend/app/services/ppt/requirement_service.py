"""Requirement domain facade: interview, outline, messages and checkpoints."""

from .services_base import PptServiceBase

class RequirementService(PptServiceBase):
    """Requirements interview, outline and project messaging operations."""
    def get(self, project_id): return self._app.requirements(project_id)
    def patch(self, project_id, payload): return self._app.patch_requirements(project_id, payload)
    def chat(self, project_id, **kwargs): return self._app.requirement_chat(project_id, **kwargs)
    def chat_stream(self, project_id, **kwargs): return self._app.requirement_chat_stream(project_id, **kwargs)
    def generate(self, project_id): return self._app.generate_requirements(project_id)
    def outline(self, project_id, page_count_target, style=None): return self._app.generate_outline(project_id, page_count_target, style)
    def message(self, project_id, content, page_id=None, option_id=None, option_label=None): return self._app.route_message(project_id, content, page_id, option_id, option_label)
    def messages(self, project_id, page_id=None): return self._app.list_messages(project_id, page_id)
    def sources(self, project_id): return self._app.list_sources(project_id)
    def checkpoints(self, project_id): return self._app.list_checkpoints(project_id)
    def confirm_checkpoint(self, project_id, code, note=None): return self._app.confirm_checkpoint(project_id, code, note)
