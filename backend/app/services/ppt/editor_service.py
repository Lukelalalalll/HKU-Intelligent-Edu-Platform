from .services_base import PptServiceBase

class EditorService(PptServiceBase):
    """Page, document, editor and assistant-facing operations."""
    def page(self, project_id, page_id): return self._app.page(project_id, page_id)
    def pages(self, project_id):
        project = self._app.project(project_id)
        return [self._app.serialize_page(p) for p in sorted(project.pages, key=lambda x: x.sort_order)]
    def serialize_page(self, page): return self._app.serialize_page(page)
    def patch_page(self, project_id, page_id, payload): return self._app.patch_page(project_id, page_id, payload)
    def action(self, project_id, page_id, action_type, replace_existing=True): return self._app.run_action(project_id, page_id, action_type, replace_existing)
    def batch(self, project_id, action_type): return self._app.run_action(project_id, None, action_type)
    def visual_selection(self, project_id, page_id, asset_ids): return self._app.save_visual_selection(project_id, page_id, asset_ids)
    def preview(self, project_id, page_id, layout_id=None): return self._app.preview_svg(project_id, page_id, layout_id)
    def document_patch(self, project_id, page_id, document, revision): return self._app.patch_document(project_id, page_id, document, revision)
    def restore(self, project_id, page_id, revision, direction): return self._app.restore_document(project_id, page_id, revision, direction)
    def upload_document(self, project_id, page_id, upload): return self._app.upload_document(project_id, page_id, upload)
