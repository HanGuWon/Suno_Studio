from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from storage.durable_storage import DurableStorage


@dataclass(slots=True)
class SubmissionEntry:
    submission_id: str
    request_id: UUID
    job_id: str | None = None
    resolved: bool = False


@dataclass(slots=True)
class APVTSSessionState:
    state_path: Path = Path("plugin/session_state.json")
    submissions: dict[str, SubmissionEntry] = field(default_factory=dict)

    def load(self) -> None:
        if not self.state_path.exists():
            return
        raw = json.loads(self.state_path.read_text())
        self.submissions = {
            sid: SubmissionEntry(
                submission_id=sid,
                request_id=UUID(entry["request_id"]),
                job_id=entry.get("job_id"),
                resolved=entry.get("resolved", False),
            )
            for sid, entry in raw.get("submissions", {}).items()
        }

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "submissions": {
                sid: {
                    "request_id": str(entry.request_id),
                    "job_id": entry.job_id,
                    "resolved": entry.resolved,
                }
                for sid, entry in self.submissions.items()
            }
        }
        self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def ensure_request_id(self, submission_id: str) -> UUID:
        existing = self.submissions.get(submission_id)
        if existing:
            return existing.request_id
        request_id = uuid4()
        self.submissions[submission_id] = SubmissionEntry(submission_id=submission_id, request_id=request_id)
        self.save()
        return request_id

    def mark_job(self, submission_id: str, *, job_id: str) -> None:
        entry = self.submissions[submission_id]
        entry.job_id = job_id
        self.save()

    def reconcile_unresolved(self, storage: DurableStorage) -> list[SubmissionEntry]:
        unresolved = [entry for entry in self.submissions.values() if entry.job_id and not entry.resolved]
        jobs = {job.id: job for job in storage.list_jobs_by_ids([entry.job_id for entry in unresolved if entry.job_id])}
        reconciled: list[SubmissionEntry] = []
        for entry in unresolved:
            job = jobs.get(entry.job_id or "")
            if job is None:
                continue
            if job.status.value in {"complete", "failed"}:
                entry.resolved = True
            reconciled.append(entry)
        if reconciled:
            self.save()
        return reconciled
