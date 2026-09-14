"""Stable Celery task entrypoints.

Handlers import application services lazily so importing the API does not
create a second SQLAlchemy session or load optional document parsers.
"""

from app.jobs.celery_app import celery_app


def process_file_processing_job(job_id: str):
    from app.services.file_processing import process_job

    return process_job(job_id)


def ingest_courseware_material(material_id: str):
    from app.services.courseware_rag.service import ingest_material

    return ingest_material(material_id)


def run_ppt_generation(job_id: str, project_id: str, user_id: str):
    from app.services.ppt_agent import _run_generation_job

    return _run_generation_job(job_id, project_id, user_id)


def run_ppt_visual_research(job_id: str, project_id: str, user_id: str):
    from app.services.ppt_agent import _run_visual_research_job

    return _run_visual_research_job(job_id, project_id, user_id)


def run_ppt_export(export_id: str, project_id: str, filename: str | None = None):
    from app.api.routes.ppt import _run_export_job

    return _run_export_job(export_id, project_id, filename)


def republish_outbox():
    from app.jobs.dispatcher import recover_outbox

    return recover_outbox()


if celery_app is not None:  # pragma: no cover - requires celery installation
    process_file_processing_job = celery_app.task(
        name="hku.file_processing.process", bind=False, max_retries=3
    )(process_file_processing_job)
    ingest_courseware_material = celery_app.task(
        name="hku.courseware.ingest", bind=False, max_retries=3
    )(ingest_courseware_material)
    run_ppt_generation = celery_app.task(
        name="hku.ppt.generation", bind=False, max_retries=3
    )(run_ppt_generation)
    run_ppt_visual_research = celery_app.task(
        name="hku.ppt.visual_research", bind=False, max_retries=3
    )(run_ppt_visual_research)
    run_ppt_export = celery_app.task(
        name="hku.ppt.export", bind=False, max_retries=3
    )(run_ppt_export)
    republish_outbox = celery_app.task(
        name="hku.system.republish_outbox", bind=False
    )(republish_outbox)
