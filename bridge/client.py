"""Plug-in side bridge client with preflight capability handshake."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    plugin_version: str
    protocol_version: str


class BridgeClient:
    def __init__(self, config: ClientConfig):
        self._config = config
        self._handshake_done = False

    def _headers(self, request_id: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Plugin-Version": self._config.plugin_version,
            "X-Protocol-Version": self._config.protocol_version,
            "X-Request-ID": request_id,
        }

    def _parse_version(self, value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split("."))

    def preflight_handshake(self, request_id: str) -> None:
        req = urllib.request.Request(
            f"{self._config.base_url}/capabilities",
            method="GET",
            headers=self._headers(request_id),
        )
        try:
            with urllib.request.urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Handshake failed with HTTP {exc.code}: {detail}") from exc

        protocol = payload.get("protocol", {})
        min_supported = protocol.get("min_supported")
        max_supported = protocol.get("max_supported")
        if not min_supported or not max_supported:
            raise RuntimeError("Handshake response missing protocol support range")

        requested = self._parse_version(self._config.protocol_version)
        if requested < self._parse_version(min_supported):
            raise RuntimeError(
                f"Protocol {self._config.protocol_version} unsupported; upgrade to >= {min_supported}"
            )
        if requested > self._parse_version(max_supported):
            raise RuntimeError(
                f"Protocol {self._config.protocol_version} unsupported; downgrade to <= {max_supported} or upgrade provider"
            )

        self._handshake_done = True

    def submit_job(self, request_id: str, body: dict) -> dict:
        if not self._handshake_done:
            self.preflight_handshake(request_id)

        req = urllib.request.Request(
            f"{self._config.base_url}/submit_job",
            method="POST",
            headers=self._headers(request_id),
            data=json.dumps(body).encode("utf-8"),
        )

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
