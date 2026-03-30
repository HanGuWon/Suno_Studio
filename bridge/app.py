from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse

from bridge.adapters import MockSunoAdapter
from bridge.errors import BridgeError, make_error
from bridge.middleware import ProtocolRange, validate_protocol_headers
from bridge.server import capabilities_payload
from bridge.services.import_service import ImportService
from bridge.services.job_service import JobService
from bridge.downloader import AssetDownloader
from bridge.models import CreateJobRequest
from bridge_security import ExpiredRequestError, ReplayDetectedError, RequestSigner, SignatureValidationError, SignedHeaders
from storage.durable_storage import DurableStorage

PROTOCOL_RANGE = ProtocolRange(min_supported="1.2", max_supported="1.3")
PROVIDER_VERSION = "0.2.0"


class BridgeContext:
    def __init__(self, storage: DurableStorage, importer: ImportService, jobs: JobService) -> None:
        self.storage = storage
        self.importer = importer
        self.jobs = jobs


def create_app(
    *,
    db_path: str | Path = "storage/jobs.db",
    assets_root: str | Path = "storage/assets",
    enable_hmac: bool | None = None,
) -> FastAPI:
    storage = DurableStorage(db_path)
    importer = ImportService(storage=storage, assets_root=Path(assets_root) / "imported")
    downloader = AssetDownloader(storage=storage, root=Path(assets_root) / "downloads")
    jobs = JobService(storage=storage, provider=MockSunoAdapter(), downloader=downloader)
    context = BridgeContext(storage=storage, importer=importer, jobs=jobs)

    app = FastAPI(title="Suno Studio Bridge", version=PROVIDER_VERSION)
    app.state.ctx = context
    app.state.protocol_range = PROTOCOL_RANGE

    should_verify = enable_hmac if enable_hmac is not None else os.getenv("BRIDGE_ENABLE_HMAC", "1") == "1"
    app.state.require_hmac = should_verify
    shared_secret = os.getenv("BRIDGE_SHARED_SECRET", "dev-shared-secret")
    signer = RequestSigner(shared_secret.encode("utf-8"))
    app.state.request_signer = signer

    @app.middleware("http")
    async def protocol_security_middleware(request, call_next):
        headers = {k: v for k, v in request.headers.items()}
        ok, error = validate_protocol_headers(
            {
                "X-Request-ID": headers.get("x-request-id", ""),
                "X-Plugin-Version": headers.get("x-plugin-version", ""),
                "X-Protocol-Version": headers.get("x-protocol-version", ""),
            },
            app.state.protocol_range,
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

        response = await call_next(request)
        return response

    @app.exception_handler(BridgeError)
    async def bridge_error_handler(_, exc: BridgeError):
        return JSONResponse(status_code=400, content=exc.to_payload())

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

    @app.post("/assets/import")
    async def post_assets_import(
        file: UploadFile = File(...),
        normalizeOnImport: bool = Form(default=False),
    ) -> dict[str, Any]:
        suffix = Path(file.filename or "upload.bin").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        try:
            manifest = context.importer.import_file(tmp_path, normalize_on_import=normalizeOnImport)
            return {"assetId": manifest["id"], "manifest": manifest}
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post("/jobs/text")
    async def post_jobs_text(payload: dict[str, Any]) -> dict[str, Any]:
        request = CreateJobRequest(
            clientRequestId=UUID(payload["clientRequestId"]),
            prompt=payload["prompt"],
            metadata=payload.get("metadata", {}),
        )
        job, created = context.jobs.create_text_job(request)
        if created:
            job = context.jobs.run_job(job.id)
        return {"created": created, "job": _job_to_dict(job)}

    @app.post("/jobs/audio")
    async def post_jobs_audio(
        clientRequestId: str = Form(...),
        prompt: str = Form(default=""),
        metadata: str = Form(default="{}"),
        assetId: str | None = Form(default=None),
        file: UploadFile | None = File(default=None),
    ) -> dict[str, Any]:
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
            raise BridgeError(
                code="AUDIO_SOURCE_REQUIRED",
                message="Provide either assetId or multipart file for audio jobs.",
                details={},
            )

        request = CreateJobRequest(
            clientRequestId=UUID(clientRequestId),
            prompt=prompt,
            metadata=json.loads(metadata),
        )
        job, created = context.jobs.create_audio_job(request, asset_id=local_asset_id)
        if created:
            job = context.jobs.run_job(job.id)
        return {"created": created, "job": _job_to_dict(job)}

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str) -> dict[str, Any]:
        job = context.storage.get_job(job_id)
        if not job:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        return _job_to_dict(job)

    @app.post("/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        try:
            job = context.jobs.cancel_job(job_id)
        except KeyError:
            raise BridgeError("JOB_NOT_FOUND", f"Job {job_id} not found", {})
        return _job_to_dict(job)

    @app.on_event("startup")
    async def on_startup() -> None:
        context.jobs.recover_inflight()

    return app


def _job_to_dict(job) -> dict[str, Any]:
    return {
        "id": job.id,
        "type": job.type.value,
        "status": job.status.value,
        "clientRequestId": str(job.client_request_id),
        "remoteProviderId": job.remote_provider_id,
        "assetId": job.asset_id,
        "outputManifest": job.output_manifest_json,
        "createdAt": job.created_at.isoformat(),
        "updatedAt": job.updated_at.isoformat(),
    }
