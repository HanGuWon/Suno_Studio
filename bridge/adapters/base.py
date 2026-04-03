from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProviderOutput:
    variant: str
    extension: str
    content: bytes


@dataclass(frozen=True)
class ProviderPollResult:
    state: str
    progress: float
    retryable_error: str | None = None


class ProviderAdapter(Protocol):
    def submit_text_job(self, *, job_id: str, prompt: str, metadata: dict) -> str:
        ...

    def submit_audio_job(self, *, job_id: str, prompt: str, metadata: dict, source_path: Path) -> str:
        ...

    def poll_job(self, remote_job_id: str) -> ProviderPollResult:
        ...

    def download_outputs(self, remote_job_id: str) -> list[ProviderOutput]:
        ...

    def cancel_remote_job(self, remote_job_id: str) -> bool:
        ...
