from __future__ import annotations

import io
import json
import threading
import time
import wave
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from bridge.app import create_app
from bridge_security import RequestSigner


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


def _wait_for_terminal(client: TestClient, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/jobs/{job_id}", headers=_headers(str(uuid4())))
        assert r.status_code == 200
        payload = r.json()
        if payload["status"] in {"complete", "failed", "cancelled"}:
            return payload
        time.sleep(0.05)
    raise TimeoutError(f"job {job_id} did not finish")


def test_non_blocking_text_job_creation_and_poll_to_completion(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        response = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "async text", "metadata": {"mock_poll_steps": 4}},
            headers=_headers("nt-1"),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["job"]["status"] in {"created", "queued_local", "submitting_remote", "polling_remote"}

        terminal = _wait_for_terminal(client, body["job"]["id"])
        assert terminal["status"] == "complete"
        assert terminal["outputAssets"]


def test_non_blocking_audio_job_creation_and_poll_to_completion(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        response = client.post(
            "/jobs/audio",
            headers=_headers("na-1"),
            data={"clientRequestId": str(uuid4()), "prompt": "audio", "metadata": "{}"},
            files={"file": ("seed.wav", _wav_bytes(), "audio/wav")},
        )
        assert response.status_code == 200
        job = response.json()["job"]
        assert job["status"] in {"created", "queued_local", "submitting_remote", "polling_remote"}
        terminal = _wait_for_terminal(client, job["id"])
        assert terminal["status"] == "complete"


def test_cancellation_before_remote_submit(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "cancel early", "metadata": {"mock_poll_steps": 10}},
            headers=_headers("c1"),
        )
        job_id = create.json()["job"]["id"]
        cancel = client.post(f"/jobs/{job_id}/cancel", headers=_headers("c2"))
        assert cancel.status_code == 200
        terminal = _wait_for_terminal(client, job_id)
        assert terminal["status"] in {"cancelled", "complete"}


def test_cancellation_during_polling(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "cancel mid", "metadata": {"mock_poll_steps": 20}},
            headers=_headers("cp1"),
        )
        job_id = create.json()["job"]["id"]

        for _ in range(20):
            state = client.get(f"/jobs/{job_id}", headers=_headers(str(uuid4()))).json()["status"]
            if state == "polling_remote":
                break
            time.sleep(0.02)

        cancel = client.post(f"/jobs/{job_id}/cancel", headers=_headers("cp2"))
        assert cancel.status_code == 200
        terminal = _wait_for_terminal(client, job_id)
        assert terminal["status"] in {"cancelled", "complete"}


def test_recovery_after_restart_midflight(tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    assets_root = tmp_path / "assets"

    with TestClient(create_app(db_path=db_path, assets_root=assets_root, enable_hmac=False)) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "recovery", "metadata": {"mock_poll_steps": 30}},
            headers=_headers("r1"),
        )
        job_id = create.json()["job"]["id"]
        time.sleep(0.05)

    with TestClient(create_app(db_path=db_path, assets_root=assets_root, enable_hmac=False)) as restarted:
        terminal = _wait_for_terminal(restarted, job_id)
        assert terminal["status"] == "complete"


def test_two_concurrent_creates_same_client_request_id(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        payload = {"clientRequestId": str(uuid4()), "prompt": "same", "metadata": {}}
        results: list[dict] = []

        def create_one(rid: str) -> None:
            res = client.post("/jobs/text", json=payload, headers=_headers(rid))
            results.append(res.json())

        t1 = threading.Thread(target=create_one, args=("cc1",))
        t2 = threading.Thread(target=create_one, args=("cc2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        ids = {item["job"]["id"] for item in results}
        assert len(ids) == 1


def test_duplicate_download_attempt_after_restart_is_deduped(tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    assets_root = tmp_path / "assets"

    with TestClient(create_app(db_path=db_path, assets_root=assets_root, enable_hmac=False)) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "dedupe", "metadata": {}},
            headers=_headers("dd1"),
        )
        job_id = create.json()["job"]["id"]
        terminal = _wait_for_terminal(client, job_id)
        first_assets = terminal["outputAssets"]

    with TestClient(create_app(db_path=db_path, assets_root=assets_root, enable_hmac=False)) as restarted:
        terminal2 = _wait_for_terminal(restarted, job_id)
        assert terminal2["outputAssets"] == first_assets


def test_cancellation_racing_with_completion(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "race", "metadata": {"mock_poll_steps": 2}},
            headers=_headers("ra1"),
        )
        job_id = create.json()["job"]["id"]
        client.post(f"/jobs/{job_id}/cancel", headers=_headers("ra2"))
        terminal = _wait_for_terminal(client, job_id)
        assert terminal["status"] in {"cancelled", "complete"}


def test_hmac_signed_requests_and_protocol_mismatch(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=True)
    with TestClient(app) as client:
        bad = client.get("/capabilities", headers={"X-Request-ID": "b1", "X-Plugin-Version": "1", "X-Protocol-Version": "9.9"})
        assert bad.status_code == 400
        assert set(bad.json()["error"].keys()) == {"code", "message", "details", "request_id"}

        payload = {"clientRequestId": str(uuid4()), "prompt": "signed", "metadata": {}}
        raw = json.dumps(payload).encode("utf-8")
        signer = RequestSigner(b"dev-shared-secret")
        sig = signer.sign(raw)
        headers = _headers("hmac1") | {
            "Content-Type": "application/json",
            "X-Signature-Timestamp": str(sig.timestamp),
            "X-Signature-Nonce": sig.nonce,
            "X-Body-Sha256": sig.body_sha256,
            "X-Signature": sig.signature,
        }
        ok = client.post("/jobs/text", data=raw, headers=headers)
        assert ok.status_code == 200


def test_manual_provider_handoff_for_text_job(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/text",
            json={
                "clientRequestId": str(uuid4()),
                "prompt": "manual handoff text",
                "providerMode": "manual_suno",
                "metadata": {"mode": "song", "request_stems": True, "request_midi": True},
            },
            headers=_headers("m1"),
        )
        assert create.status_code == 200
        job = create.json()["job"]
        assert job["providerMode"] == "manual_suno"

        for _ in range(20):
            refreshed = client.get(f"/jobs/{job['id']}", headers=_headers(str(uuid4()))).json()
            if refreshed["status"] == "awaiting_manual_provider_result":
                break
            time.sleep(0.02)
        assert refreshed["status"] == "awaiting_manual_provider_result"

        handoff = client.get(f"/jobs/{job['id']}/handoff", headers=_headers("m2"))
        assert handoff.status_code == 200
        payload = handoff.json()
        assert payload["handoff"]["requested_deliverables"]["stems"] is True
        assert Path(payload["workspace"]).exists()


def test_manual_provider_audio_job_and_manual_complete(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/audio",
            headers=_headers("ma1"),
            data={
                "clientRequestId": str(uuid4()),
                "prompt": "manual audio",
                "metadata": json.dumps({"mode": "audio_prompt", "request_mix": True, "request_midi": True}),
                "providerMode": "manual_suno",
            },
            files={"file": ("seed.wav", _wav_bytes(), "audio/wav")},
        )
        assert create.status_code == 200
        job_id = create.json()["job"]["id"]
        for _ in range(20):
            refreshed = client.get(f"/jobs/{job_id}", headers=_headers(str(uuid4()))).json()
            if refreshed["status"] == "awaiting_manual_provider_result":
                break
            time.sleep(0.02)
        assert refreshed["status"] == "awaiting_manual_provider_result"

        complete = client.post(
            f"/jobs/{job_id}/manual-complete",
            headers=_headers("ma2"),
            files={
                "mixFiles": ("result.wav", _wav_bytes(), "audio/wav"),
                "midiFiles": ("result.mid", b"MThd....", "audio/midi"),
            },
        )
        assert complete.status_code == 200
        body = complete.json()
        assert body["status"] == "complete"
        assert body["outputManifest"]["importedDeliverables"]["mix"]
        assert body["outputManifest"]["importedDeliverables"]["midi"]


def test_mock_provider_regression_still_completes(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        create = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "mock still works", "providerMode": "mock_suno", "metadata": {}},
            headers=_headers("rg1"),
        )
        assert create.status_code == 200
        terminal = _wait_for_terminal(client, create.json()["job"]["id"])
        assert terminal["status"] == "complete"


def test_beta_bridge_rejects_placeholder_provider_modes(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        response = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "placeholder", "providerMode": "official_api", "metadata": {}},
            headers=_headers("bp1"),
        )
        assert response.status_code == 400
        payload = response.json()["error"]
        assert payload["code"] == "INVALID_PROVIDER_MODE"
        assert payload["details"]["supported"] == ["mock_suno", "manual_suno"]
        assert payload["details"]["futureScope"] == ["official_api", "web_session"]


def test_beta_bridge_rejects_unknown_provider_modes(tmp_path: Path):
    app = create_app(db_path=tmp_path / "jobs.db", assets_root=tmp_path / "assets", enable_hmac=False)
    with TestClient(app) as client:
        response = client.post(
            "/jobs/text",
            json={"clientRequestId": str(uuid4()), "prompt": "unknown", "providerMode": "totally_unknown", "metadata": {}},
            headers=_headers("bp2"),
        )
        assert response.status_code == 400
        payload = response.json()["error"]
        assert payload["code"] == "INVALID_PROVIDER_MODE"
        assert payload["details"]["providerMode"] == "totally_unknown"
        assert payload["details"]["supported"] == ["mock_suno", "manual_suno"]
