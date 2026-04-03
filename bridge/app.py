from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse

from bridge.adapters import ManualSunoAdapter, MockSunoAdapter
from bridge.downloader import AssetDownloader
from bridge.errors import BridgeError, make_error
from bridge.middleware import ProtocolRange, validate_protocol_headers
from bridge.models import CreateJobRequest, JobStatus, ProviderMode
from bridge.schemas.api_models import AssetImportResponse, JobCreateResponse, JobStatusResponse, ManualHandoffResponse, TextJobCreateRequest
from bridge.server import capabilities_payload
from bridge.services.import_service import ImportService
from bridge.services.job_service import JobOrchestrator, JobService
from bridge_security import ExpiredRequestError, ReplayDetectedError, RequestSigner, SignatureValidationError, SignedHeaders
from storage.durable_storage import DurableStorage

PROTOCOL_RANGE = ProtocolRange(min_supported="1.2", max_supported="1.3")
PROVIDER_VERSION = "0.3.0"


class BridgeContext:
    def __init__(self, storage: DurableStorage, importer: ImportService, jobs: JobService, orchestrator: JobOrchestrator) -> None:
        self.storage = storage
        self.importer = importer
        self.jobs = jobs
        self.orchestrator = orchestrator


def create_app(
    *,
    db_path: str | Path = "storage/jobs.db",
    assets_root: str | Path = "storage/assets",
    enable_hmac: bool | None = None,
    shared_secret: str | None = None,
) -> FastAPI:
    storage = DurableStorage(db_path)
    importer = ImportService(storage=storage, assets_root=Path(assets_root) / "imported")
    downloader = AssetDownloader(storage=storage, root=Path(assets_root) / "downloads")
    manual_adapter = ManualSunoAdapter(Path(assets_root).parent / "provider_workspaces")
    orchestrator = JobOrchestrator(
        storage=storage,
        providers={
            ProviderMode.MOCK_SUNO: MockSunoAdapter(),
            ProviderMode.MANUAL_SUNO: manual_adapter,
        },
        downloader=downloader,
    )
    jobs = JobService(storage=storage, orchestrator=orchestrator)

    context = BridgeContext(storage=storage, importer=importer, jobs=jobs, orchestrator=orchestrator)
    app = FastAPI(title="Suno Studio Bridge", version=PROVIDER_VERSION)
    app.state.ctx = context

    should_verify = enable_hmac if enable_hmac is not None else True
    app.state.require_hmac = should_verify
    app.state.request_signer = RequestSigner((shared_secret or "dev-shared-secret").encode("utf-8"))

    @app.middleware("http")
    async def protocol_security_middleware(request, call_next):
        headers = {k: v for k, v in request.headers.items()}
        ok, error = validate_protocol_headers(
            {
                "X-Request-ID": headers.get("x-request-id", ""),
                "X-Plugin-Version": headers.get("x-plugin-version", ""),
                "X-Protocol-Version": headers.get("x-protocol-version", ""),
            },
            PROTOCOL_RANGE,
        )
        if not ok:
            return JSONResponse(status_code=400, content=error)

        if app.state.require_hmac and request.url.path != "/capabilities":
            body = await request.body()
            try:
                signed = SignedHeaders(
                    timestamp=int(headers.get("x-signature-timestamp", "0")),
                    nonce=headers.get("x-signature-nonce", ""),
                    body_sha256=headers.get("x-body-sha256", ""),
                    signature=headers.get("x-signature", ""),
                )
                app.state.request_signer.verify(signed, body)
            except (ValueError, SignatureValidationError, ExpiredRequestError, ReplayDetectedError) as exc:
                return JSONResponse(
                    status_code=401,
                    content=make_error(
                        "AUTH_SIGNATURE_INVALID",
                        "Request signature validation failed",
                        details={"reason": str(exc)},
                        request_id=headers.get("x-request-id"),
                    ),
                )

            async def receive_once() -> dict[str, Any]:
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive_once

        return await call_next(request)

    @app.exception_handler(BridgeError)
    async def bridge_error_handler(_, exc: BridgeError):
        status_code = 404 if exc.code.endswith("NOT_FOUND") else 400
        return JSONResponse(status_code=status_code, content=exc.to_payload())

    @app.on_event("startup")
    async def on_startup() -> None:
        context.orchestrator.start()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        context.orchestrator.stop()

    @app.get("/capabilities")
    async def get_capabilities(
        x_request_id: Annotated[str, Header(alias="X-Request-ID")],
    ) -> dict[str, Any]:
        payload = capabilities_payload(
            provider_version=PROVIDER_VERSION,
            min_supported=PROTOCOL_RANGE.min_supported,
            max_supported=PROTOCOL_RANGE.max_supported,
        )
        payload["requestId"] = x_request_id
        payload["auth"] = {
            "hmacRequired": app.state.require_hmac,
            "signatureHeaders": [
                "X-Signature-Timestamp",
                "X-Signature-Nonce",
                "X-Body-Sha256",
                "X-Signature",
            ],
        }
        return payload

    @app.post("/assets/import", response_model=AssetImportResponse)
    async def post_assets_import(
        file: UploadFile = File(...),
        normalizeOnImport: bool = Form(default=False),
    ) -> AssetImportResponse:
        suffix = Path(file.filename or "upload.bin").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        try:
            manifest = context.importer.import_file(tmp_path, normalize_on_import=normalizeOnImport)
            return AssetImportResponse(assetId=manifest["id"], manifest=manifest)
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post("/jobs/text", response_model=JobCreateResponse)
    async def post_jobs_text(payload: TextJobCreateRequest) -> JobCreateResponse:
        request = CreateJobRequest(
            clientRequestId=payload.clientRequestId,
            prompt=payload.prompt,
            metadata=payload.metadata,
        )
        provider_mode = ProviderMode(payload.providerMode)
        job, created = context.jobs.create_text_job(request, provider_mode=provider_mode)
        return JobCreateResponse(created=created, job=_job_to_response(job))

    @app.post("/jobs/audio", response_model=JobCreateResponse)
    async def post_jobs_audio(
        clientRequestId: str = Form(...),
        prompt: str = Form(default=""),
        metadata: str = Form(default="{}"),
        providerMode: str = Form(default="mock_suno"),
        assetId: str | None = Form(default=None),
        file: UploadFile | None = File(default=None),
    ) -> JobCreateResponse:
        local_asset_id = assetId
        if file is not None:
            suffix = Path(file.filename or "upload.bin").suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await file.read())
                tmp_path = Path(tmp.name)
            try:
                manifest = context.importer.import_file(tmp_path, normalize_on_import=False)
                local_asset_id = manifest["id"]
            finally:
                tmp_path.unlink(missing_ok=True)

        if not local_asset_id:
            raise BridgeError("AUDIO_SOURCE_REQUIRED", "Provide either assetId or multipart file for audio jobs.", {})

        request = CreateJobRequest(
            clientRequestId=UUID(clientRequestId),
            prompt=prompt,
            metadata=json.loads(metadata),
        )
        provider_mode = ProviderMode(providerMode)
        job, created = context.jobs.create_audio_job(request, asset_id=local_asset_id, provider_mode=provider_mode)
        return JobCreateResponse(created=created, job=_job_to_response(job))

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    async def get_job(job_id: str) -> JobStatusResponse:
        job = context.storage.get_job(job_id)
        if not job:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        return _job_to_response(job)

    @app.post("/jobs/{job_id}/cancel", response_model=JobStatusResponse)
    async def cancel_job(job_id: str) -> JobStatusResponse:
        try:
            job = context.jobs.cancel_job(job_id)
        except KeyError:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        return _job_to_response(job)

    @app.get("/jobs/{job_id}/handoff", response_model=ManualHandoffResponse)
    async def get_job_handoff(job_id: str) -> ManualHandoffResponse:
        job = context.storage.get_job(job_id)
        if not job:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        if job.provider_mode is not ProviderMode.MANUAL_SUNO:
            raise BridgeError("INVALID_PROVIDER_MODE", "Handoff only exists for manual_suno jobs.", {"providerMode": job.provider_mode.value})
        handoff = job.provider_metadata.get("handoff")
        if not handoff:
            raise BridgeError("HANDOFF_NOT_READY", "Manual handoff package has not been prepared yet.", {"jobId": job_id})
        return ManualHandoffResponse(
            jobId=job.id,
            providerMode=job.provider_mode.value,
            workspace=handoff["workspace"],
            instructionsPath=handoff["instructionsPath"],
            handoff=handoff["handoff"],
        )

    @app.post("/jobs/{job_id}/manual-complete", response_model=JobStatusResponse)
    async def post_manual_complete(
        job_id: str,
        mixFiles: list[UploadFile] = File(default=[]),
        stemFiles: list[UploadFile] = File(default=[]),
        tempoLockedStemFiles: list[UploadFile] = File(default=[]),
        midiFiles: list[UploadFile] = File(default=[]),
    ) -> JobStatusResponse:
        job = context.storage.get_job(job_id)
        if not job:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        if job.provider_mode is not ProviderMode.MANUAL_SUNO:
            raise BridgeError("INVALID_PROVIDER_MODE", "manual-complete only supported for manual_suno jobs.", {})

        all_files = {"mix": mixFiles, "stems": stemFiles, "tempo_locked_stems": tempoLockedStemFiles, "midi": midiFiles}
        if not any(all_files.values()):
            raise BridgeError("NO_FILES", "Provide at least one imported manual result file.", {})

        context.storage.set_job_status(job_id, JobStatus.IMPORTING_PROVIDER_RESULT, progress=0.85)
        imported_files: list[dict[str, str]] = []
        output_assets: list[str] = []
        for family, files in all_files.items():
            for upload in files:
                suffix = Path(upload.filename or "output.bin").suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(await upload.read())
                    tmp_path = Path(tmp.name)
                try:
                    path, _ = downloader.store_download(
                        job_id=job_id,
                        variant=f"manual_{family}",
                        content=tmp_path.read_bytes(),
                        ext=suffix.lstrip(".") or "bin",
                    )
                finally:
                    tmp_path.unlink(missing_ok=True)
                imported_files.append({"family": family, "path": str(path), "name": upload.filename or path.name})
                output_assets.append(str(path))

        requested = (job.provider_metadata.get("handoff") or {}).get("handoff", {}).get("requested_deliverables", {})
        manifest = {
            "providerMode": job.provider_mode.value,
            "requestedDeliverables": requested,
            "importedDeliverables": {
                "mix": [f for f in imported_files if f["family"] == "mix"],
                "stems": [f for f in imported_files if f["family"] == "stems"],
                "tempoLockedStems": [f for f in imported_files if f["family"] == "tempo_locked_stems"],
                "midi": [f for f in imported_files if f["family"] == "midi"],
            },
            "files": imported_files,
        }
        context.storage.attach_job_artifacts(job_id, output_manifest=manifest, output_assets=output_assets)
        completed = context.storage.set_job_status(job_id, JobStatus.COMPLETE, progress=1.0, last_error=None)
        return _job_to_response(completed)

    return app


def _job_to_response(job) -> JobStatusResponse:
    return JobStatusResponse(
        id=job.id,
        type=job.type.value,
        status=job.status.value,
        clientRequestId=str(job.client_request_id),
        remoteJobId=job.remote_job_id,
        assetId=job.asset_id,
        progress=job.progress,
        lastError=job.last_error,
        outputAssets=job.output_assets,
        outputManifest=job.output_manifest_json,
        providerMode=job.provider_mode.value,
        providerMetadata=job.provider_metadata,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )
