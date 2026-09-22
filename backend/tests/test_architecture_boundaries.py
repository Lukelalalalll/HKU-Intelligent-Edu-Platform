from app.jobs.dispatcher import JobHandle, _retry_at
from app.jobs.manager import JobManager
from app.services.file_processing.parsers import default_registry
from app.main import app


def test_parser_registry_exposes_capability_boundary(tmp_path):
    registry = default_registry()
    parser = registry.resolve(".txt", "text/plain")
    assert parser.name == "text"
    source = tmp_path.joinpath("notes.txt")
    source.write_text("hello", encoding="utf-8")
    result = parser.parse(source, tmp_path)
    # The parser boundary is explicit even when the source file is small.
    assert result.parser == "native_text"


def test_retry_backoff_is_monotonic():
    first = _retry_at(1)
    second = _retry_at(2)
    assert second > first


def test_job_handle_is_stable_value_object():
    handle = JobHandle(id="job-1", kind="file_processing", status="pending")
    assert handle.id == "job-1"
    assert handle.kind == "file_processing"
    assert all(hasattr(JobManager, method) for method in ("enqueue", "cancel", "retry", "recover_stale_jobs"))


def test_v2_contract_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v2/ppt/projects/{project_id}/generation" in paths
    assert "/api/v2/ppt/projects/{project_id}/exports" in paths
    assert "/api/v2/files" in paths
