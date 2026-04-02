from __future__ import annotations

from bridge.services.job_service import JobOrchestrator


class StartupRecoveryWorker:
    """Compatibility wrapper around async orchestrator recovery."""

    def __init__(self, orchestrator: JobOrchestrator) -> None:
        self.orchestrator = orchestrator

    def run_once(self) -> list[str]:
        return self.orchestrator.recover_inflight_jobs()
