from __future__ import annotations

from pathlib import Path

from bridge.adapters.base import ProviderAdapter, ProviderOutput


class MockSunoAdapter(ProviderAdapter):
    """Deterministic adapter used for integration tests and local MVP."""

    def submit_text_job(self, *, job_id: str, prompt: str, metadata: dict) -> str:
        return f"mock-text-{job_id}"

    def submit_audio_job(self, *, job_id: str, prompt: str, metadata: dict, source_path: Path) -> str:
        return f"mock-audio-{job_id}"

    def poll_job(self, remote_job_id: str) -> str:
        return "ready"

    def download_outputs(self, remote_job_id: str) -> list[ProviderOutput]:
        payload = f"MOCK_OUTPUT::{remote_job_id}".encode("utf-8")
        return [ProviderOutput(variant="main", extension="wav", content=payload)]
