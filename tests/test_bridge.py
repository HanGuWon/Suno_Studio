from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from bridge.adapters import MockSunoAdapter
from bridge.api import BridgeAPI
from bridge.downloader import AssetDownloader
from bridge.models import CreateJobRequest, JobStatus
from bridge.services.job_service import JobOrchestrator, JobService
from plugin.session_state import APVTSSessionState
from storage.durable_storage import DurableStorage


def _api(tmp_path):
    storage = DurableStorage(tmp_path / "jobs.db")
    downloader = AssetDownloader(storage, root=tmp_path / "assets")
    orchestrator = JobOrchestrator(storage=storage, provider=MockSunoAdapter(), downloader=downloader)
    orchestrator.start()
    service = JobService(storage=storage, orchestrator=orchestrator)
    return storage, BridgeAPI(service), orchestrator


def test_idempotent_create_for_text_and_audio(tmp_path):
    _, api, orchestrator = _api(tmp_path)
    try:
        request_id = uuid4()
        request = CreateJobRequest(prompt="hello", clientRequestId=request_id)
        first, created = api.post_jobs_text(request)
        second, created_again = api.post_jobs_text(request)

        assert created is True
        assert created_again is False
        assert first.id == second.id

        audio_request = CreateJobRequest(prompt="sound", clientRequestId=request_id)
        audio, audio_created = api.post_jobs_audio(audio_request, asset_id="asset-1")
        assert audio_created is True
        assert audio.type.value == "audio"
    finally:
        orchestrator.stop()


def test_concurrent_idempotent_create(tmp_path):
    _, api, orchestrator = _api(tmp_path)
    try:
        request = CreateJobRequest(prompt="concurrent", clientRequestId=uuid4())

        def call_create():
            return api.post_jobs_text(request)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [f.result() for f in [pool.submit(call_create), pool.submit(call_create)]]

        job_ids = {result[0].id for result in results}
        created_flags = [result[1] for result in results]
        assert len(job_ids) == 1
        assert created_flags.count(True) == 1
        assert created_flags.count(False) == 1
    finally:
        orchestrator.stop()


def test_plugin_state_generates_and_reconciles_without_duplicates(tmp_path):
    storage, api, orchestrator = _api(tmp_path)
    try:
        session = APVTSSessionState(state_path=tmp_path / "session.json")
        session.load()

        request_id = session.ensure_request_id("submit-1")
        same_request_id = session.ensure_request_id("submit-1")
        assert request_id == same_request_id

        job, _ = api.post_jobs_text(CreateJobRequest(prompt="melody", clientRequestId=request_id))
        session.mark_job("submit-1", job_id=job.id)

        # wait for worker to complete deterministically
        for _ in range(100):
            current = storage.get_job(job.id)
            if current and current.status == JobStatus.COMPLETE:
                break
            import time
            time.sleep(0.01)
        reconciled = session.reconcile_unresolved(storage)
        assert len(reconciled) == 1
        assert reconciled[0].resolved is True
    finally:
        orchestrator.stop()
