"""Plug-in side bridge client with async-job helpers and preflight handshake."""

from __future__ import annotations

import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bridge.errors import BridgeError
from bridge_security import RequestSigner


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    plugin_version: str
    protocol_version: str
    shared_secret: str = "dev-shared-secret"


class BridgeClient:
    def __init__(self, config: ClientConfig):
        self._config = config
        self._handshake_done = False
        self._signer = RequestSigner(config.shared_secret.encode("utf-8"))
        self._hmac_required = True

    @classmethod
    def from_discovery_file(cls, lockfile: str | Path, *, plugin_version: str, protocol_version: str, shared_secret: str) -> "BridgeClient":
        payload = json.loads(Path(lockfile).read_text(encoding="utf-8"))
        base_url = f"http://{payload['host']}:{payload['port']}"
        return cls(
            ClientConfig(
                base_url=base_url,
                plugin_version=plugin_version,
                protocol_version=protocol_version,
                shared_secret=shared_secret,
            )
        )

    def _headers(self, request_id: str, body: bytes = b"", *, include_json: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Plugin-Version": self._config.plugin_version,
            "X-Protocol-Version": self._config.protocol_version,
            "X-Request-ID": request_id,
        }
        if include_json:
            headers["Content-Type"] = "application/json"

        if self._hmac_required:
            signed = self._signer.sign(body)
            headers["X-Signature-Timestamp"] = str(signed.timestamp)
            headers["X-Signature-Nonce"] = signed.nonce
            headers["X-Body-Sha256"] = signed.body_sha256
            headers["X-Signature"] = signed.signature
        return headers

    def _parse_version(self, value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split("."))

    def preflight_handshake(self, request_id: str) -> None:
        req = urllib.request.Request(
            f"{self._config.base_url}/capabilities",
            method="GET",
            headers=self._headers(request_id, include_json=False),
        )
        payload = self._urlopen_json(req)
        protocol = payload.get("protocol", {})
        min_supported = protocol.get("min_supported")
        max_supported = protocol.get("max_supported")
        if not min_supported or not max_supported:
            raise RuntimeError("Handshake response missing protocol support range")

        requested = self._parse_version(self._config.protocol_version)
        if requested < self._parse_version(min_supported):
            raise RuntimeError(f"Protocol {self._config.protocol_version} unsupported; upgrade to >= {min_supported}")
        if requested > self._parse_version(max_supported):
            raise RuntimeError(
                f"Protocol {self._config.protocol_version} unsupported; downgrade to <= {max_supported} or upgrade provider"
            )

        auth = payload.get("auth", {})
        self._hmac_required = bool(auth.get("hmacRequired", True))
        self._handshake_done = True

    def _ensure_handshake(self) -> None:
        if not self._handshake_done:
            self.preflight_handshake(str(uuid.uuid4()))

    def create_text_job(self, *, client_request_id: str, prompt: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_handshake()
        body = json.dumps({"clientRequestId": client_request_id, "prompt": prompt, "metadata": metadata or {}}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._config.base_url}/jobs/text",
            method="POST",
            headers=self._headers(str(uuid.uuid4()), body),
            data=body,
        )
        return self._urlopen_json(req)

    def create_audio_job(
        self,
        *,
        client_request_id: str,
        prompt: str = "",
        metadata: dict[str, Any] | None = None,
        asset_id: str | None = None,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_handshake()
        if not asset_id and not file_path:
            raise ValueError("audio job requires asset_id or file_path")
        boundary = f"----BridgeBoundary{uuid.uuid4().hex}"
        body = self._build_audio_multipart(
            boundary=boundary,
            client_request_id=client_request_id,
            prompt=prompt,
            metadata=metadata or {},
            asset_id=asset_id,
            file_path=file_path,
        )
        headers = self._headers(str(uuid.uuid4()), body, include_json=False)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = urllib.request.Request(f"{self._config.base_url}/jobs/audio", method="POST", headers=headers, data=body)
        return self._urlopen_json(req)

    def import_asset(self, file_path: str, *, normalize_on_import: bool = False) -> dict[str, Any]:
        self._ensure_handshake()
        boundary = f"----BridgeBoundary{uuid.uuid4().hex}"
        path = Path(file_path)
        chunks = [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="normalizeOnImport"\r\n\r\n',
            ("true" if normalize_on_import else "false").encode(),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(chunks)
        headers = self._headers(str(uuid.uuid4()), body, include_json=False)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = urllib.request.Request(f"{self._config.base_url}/assets/import", method="POST", headers=headers, data=body)
        return self._urlopen_json(req)

    def get_job(self, job_id: str) -> dict[str, Any]:
        self._ensure_handshake()
        req = urllib.request.Request(
            f"{self._config.base_url}/jobs/{urllib.parse.quote(job_id)}",
            method="GET",
            headers=self._headers(str(uuid.uuid4()), include_json=False),
        )
        return self._urlopen_json(req)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        self._ensure_handshake()
        req = urllib.request.Request(
            f"{self._config.base_url}/jobs/{urllib.parse.quote(job_id)}/cancel",
            method="POST",
            headers=self._headers(str(uuid.uuid4()), b"{}"),
            data=b"{}",
        )
        return self._urlopen_json(req)

    def wait_for_job(self, job_id: str, *, timeout_seconds: float = 10.0, poll_interval_seconds: float = 0.05) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            job = self.get_job(job_id)
            status = job["status"]
            if status in {"complete", "failed", "cancelled"}:
                return job
            time.sleep(poll_interval_seconds)
        raise TimeoutError(f"Timed out waiting for job {job_id}")

    def _build_audio_multipart(
        self,
        *,
        boundary: str,
        client_request_id: str,
        prompt: str,
        metadata: dict[str, Any],
        asset_id: str | None,
        file_path: str | None,
    ) -> bytes:
        chunks: list[bytes] = []

        def add_field(name: str, value: str) -> None:
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    value.encode(),
                    b"\r\n",
                ]
            )

        add_field("clientRequestId", client_request_id)
        add_field("prompt", prompt)
        add_field("metadata", json.dumps(metadata))
        if asset_id:
            add_field("assetId", asset_id)
        if file_path:
            path = Path(file_path)
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
                    b"Content-Type: application/octet-stream\r\n\r\n",
                    path.read_bytes(),
                    b"\r\n",
                ]
            )

        chunks.append(f"--{boundary}--\r\n".encode())
        return b"".join(chunks)

    def _urlopen_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail)
                if "error" in payload:
                    error = payload["error"]
                    raise BridgeError(
                        code=error.get("code", "HTTP_ERROR"),
                        message=error.get("message", "HTTP request failed"),
                        details=error.get("details", {}),
                        request_id=error.get("request_id"),
                    )
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"Bridge HTTP {exc.code}: {detail}") from exc
