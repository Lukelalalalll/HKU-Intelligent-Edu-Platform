from .services_base import PptServiceBase

class GenerationService(PptServiceBase):
    """Durable generation and visual-research job operations."""
    def start(self, project_id): return self._app.start_generation(project_id)
    def start_visual(self, project_id): return self._app.start_visual_research(project_id)
    def get_job(self, project_id, job_id): return self._app.generation_job(project_id, job_id)
    def cancel(self, project_id, job_id): return self._app.cancel_generation(project_id, job_id)
    def retry(self, project_id, job_id):
        self._app.cancel_generation(project_id, job_id)
        return self._app.start_generation(project_id)
    def design(self, project_id): return self._app.generate_design(project_id)
