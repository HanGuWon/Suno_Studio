from __future__ import annotations

from pathlib import Path

from bridge.adapters.base import ProviderAdapter, ProviderOutput, ProviderPollResult


class MockSunoAdapter(ProviderAdapter):
    """Deterministic adapter for async orchestration and tests.

    Metadata knobs for tests:
    - metadata["mock_fail_once"] = True -> first poll yields retryable error.
    - metadata["mock_poll_steps"] = int -> number of in-progress polls before ready.
    """

    def __init__(self) -> None:
        self._states: dict[str, dict] = {}

    def submit_text_job(self, *, job_id: str, prompt: str, metadata: dict) -> str:
        remote_id = f"mock-text-{job_id}"
        self._states[remote_id] = self._initial_state(prompt=prompt, metadata=metadata)
        return remote_id

    def submit_audio_job(self, *, job_id: str, prompt: str, metadata: dict, source_path: Path) -> str:
        remote_id = f"mock-audio-{job_id}"
        self._states[remote_id] = self._initial_state(prompt=prompt, metadata=metadata, source=str(source_path))
        return remote_id

    def poll_job(self, remote_job_id: str) -> ProviderPollResult:
        state = self._states[remote_job_id]
        if state["cancelled"]:
            return ProviderPollResult(state="cancelled", progress=state["progress"])

        state["poll_count"] += 1

        if state["fail_once"] and not state["failed_once"]:
            state["failed_once"] = True
            return ProviderPollResult(state="retryable_error", progress=state["progress"], retryable_error="transient")

        if state["poll_count"] == 1:
            state["progress"] = 0.1
            return ProviderPollResult(state="queued", progress=state["progress"])

        if state["poll_count"] <= state["poll_steps"]:
            state["progress"] = min(0.9, state["progress"] + 0.3)
            return ProviderPollResult(state="in_progress", progress=state["progress"])

        state["progress"] = 1.0
        return ProviderPollResult(state="ready", progress=1.0)

    def download_outputs(self, remote_job_id: str) -> list[ProviderOutput]:
        state = self._states[remote_job_id]
        payload = f"MOCK_OUTPUT::{remote_job_id}::{state['prompt']}".encode("utf-8")
        return [ProviderOutput(variant="main", extension="wav", content=payload)]

    def cancel_remote_job(self, remote_job_id: str) -> bool:
        if remote_job_id not in self._states:
            return False
        self._states[remote_job_id]["cancelled"] = True
        return True

    def _initial_state(self, *, prompt: str, metadata: dict, source: str | None = None) -> dict:
        return {
            "prompt": prompt,
            "source": source,
            "poll_count": 0,
            "poll_steps": int(metadata.get("mock_poll_steps", 3)),
            "progress": 0.0,
            "fail_once": bool(metadata.get("mock_fail_once", False)),
            "failed_once": False,
            "cancelled": False,
        }
