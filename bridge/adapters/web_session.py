from __future__ import annotations

from pathlib import Path

from bridge.adapters.base import ProviderAdapter, ProviderOutput


class WebSessionAdapter(ProviderAdapter):
    """Not yet implemented. Placeholder for future authenticated web session support."""

    def submit_text_job(self, *, job_id: str, prompt: str, metadata: dict) -> str:
        raise NotImplementedError("Web session adapter is not implemented yet")

    def submit_audio_job(self, *, job_id: str, prompt: str, metadata: dict, source_path: Path) -> str:
        raise NotImplementedError("Web session adapter is not implemented yet")

    def poll_job(self, remote_job_id: str) -> str:
        raise NotImplementedError("Web session adapter is not implemented yet")

    def download_outputs(self, remote_job_id: str) -> list[ProviderOutput]:
        raise NotImplementedError("Web session adapter is not implemented yet")
