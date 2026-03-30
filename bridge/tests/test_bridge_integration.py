from __future__ import annotations

import io
import json
import wave
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from bridge.app import create_app
from bridge.models import CreateJobRequest
from bridge.services.job_service import JobService
from storage.durable_storage import DurableStorage


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes((b"\x00\x00" * 1024))
    return buf.getvalue()


def _headers(request_id: str) -> dict[str, str]:
    return {
        "X-Request-ID": request_id,
        "X-Plugin-Version": "2.0.0",
        "X-Protocol-Version": "1.3",
    }


def test_idempotent_duplicate_create_with_same_client_request_id(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)

    payload = {
        "clientRequestId": str(uuid4()),
        "prompt": "warm pad",
        "metadata": {"mode": "song"},
    }

    first = client.post("/jobs/text", json=payload, headers=_headers("req-1"))
    second = client.post("/jobs/text", json=payload, headers=_headers("req-2"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["job"]["id"] == second.json()["job"]["id"]


def test_audio_import_manifest_creation(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)

    response = client.post(
        "/assets/import",
        files={"file": ("input.wav", _wav_bytes(), "audio/wav")},
        data={"normalizeOnImport": "false"},
        headers=_headers("imp-1"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assetId"]
    manifest = payload["manifest"]
    assert manifest["id"] == payload["assetId"]
    assert manifest["checksum"]["algorithm"] == "sha256"


def test_text_job_flow_to_completed_asset(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)

    text = client.post(
        "/jobs/text",
        json={"clientRequestId": str(uuid4()), "prompt": "house loop", "metadata": {}},
        headers=_headers("h-1"),
    )
    assert text.status_code == 200
    job = text.json()["job"]
    assert job["status"] == "complete"
    assert Path(job["outputManifest"]["files"][0]["path"]).exists()


def test_audio_job_flow_to_completed_asset(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)

    response = client.post(
        "/jobs/audio",
        headers=_headers("h-2"),
        data={
            "clientRequestId": str(uuid4()),
            "prompt": "process",
            "metadata": "{}",
        },
        files={"file": ("seed.wav", _wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == "complete"
    assert job["assetId"] is not None


def test_recovery_of_inflight_jobs_after_restart(tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    assets_root = tmp_path / "assets"

    app = create_app(db_path=db_path, assets_root=assets_root, enable_hmac=False)
    client = TestClient(app)
    response = client.post(
        "/jobs/text",
        json={"clientRequestId": str(uuid4()), "prompt": "seed", "metadata": {}},
        headers=_headers("r-1"),
    )
    assert response.status_code == 200

    storage = DurableStorage(db_path)
    downloader = app.state.ctx.jobs.downloader
    provider = app.state.ctx.jobs.provider
    service = JobService(storage=storage, provider=provider, downloader=downloader)
    created, _ = service.create_text_job(CreateJobRequest(clientRequestId=uuid4(), prompt="recover", metadata={}))

    service.recover_inflight()
    recovered_job = storage.get_job(created.id)
    assert recovered_job is not None
    assert recovered_job.status.value == "complete"


def test_protocol_mismatch_failures_and_error_shape(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)

    response = client.get(
        "/capabilities",
        headers={
            "X-Request-ID": "bad-1",
            "X-Plugin-Version": "2.0.0",
            "X-Protocol-Version": "9.9",
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert set(payload["error"].keys()) == {"code", "message", "details", "request_id"}


def test_hmac_signing_required_when_enabled(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=True)
    client = TestClient(app)

    payload = {"clientRequestId": str(uuid4()), "prompt": "secure", "metadata": {}}
    raw = json.dumps(payload).encode("utf-8")

    unsigned = client.post(
        "/jobs/text",
        data=raw,
        headers=_headers("s-1") | {"Content-Type": "application/json"},
    )
    assert unsigned.status_code == 401

    from bridge_security import RequestSigner

    signer = RequestSigner(b"dev-shared-secret")
    signed = signer.sign(raw)
    signed_headers = _headers("s-2") | {
        "Content-Type": "application/json",
        "X-Signature-Timestamp": str(signed.timestamp),
        "X-Signature-Nonce": signed.nonce,
        "X-Body-Sha256": signed.body_sha256,
        "X-Signature": signed.signature,
    }
    ok = client.post("/jobs/text", data=raw, headers=signed_headers)
    assert ok.status_code == 200


def test_downloaded_asset_deduplication(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    client = TestClient(app)
    payload = {"clientRequestId": str(uuid4()), "prompt": "dup", "metadata": {}}

    first = client.post("/jobs/text", json=payload, headers=_headers("d1"))
    second = client.post("/jobs/text", json=payload, headers=_headers("d2"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job"]["outputManifest"] == second.json()["job"]["outputManifest"]
