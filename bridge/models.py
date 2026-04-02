from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class JobType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED_LOCAL = "queued_local"
    SUBMITTING_REMOTE = "submitting_remote"
    POLLING_REMOTE = "polling_remote"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


TERMINAL_STATES = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
IN_FLIGHT_STATES = {
    JobStatus.CREATED,
    JobStatus.QUEUED_LOCAL,
    JobStatus.SUBMITTING_REMOTE,
    JobStatus.POLLING_REMOTE,
    JobStatus.DOWNLOADING,
    JobStatus.CANCELLING,
}


@dataclass(slots=True)
class CreateJobRequest:
    prompt: str
    clientRequestId: UUID
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Job:
    id: str
    type: JobType
    status: JobStatus
    client_request_id: UUID
    payload: dict[str, Any]
    remote_job_id: str | None = None
    asset_id: str | None = None
    output_manifest_json: dict[str, Any] | None = None
    output_assets: list[str] = field(default_factory=list)
    progress: float = 0.0
    last_error: str | None = None
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class JobTransition:
    job_id: str
    from_status: JobStatus
    to_status: JobStatus
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None
