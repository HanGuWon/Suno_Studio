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
    SUBMITTED = "submitted"
    POLLING = "polling"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
IN_FLIGHT_STATES = {
    JobStatus.CREATED,
    JobStatus.SUBMITTED,
    JobStatus.POLLING,
    JobStatus.DOWNLOADING,
}


@dataclass(slots=True)
class CreateJobRequest:
    """API-level create payload with idempotency key."""

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
    remote_provider_id: str | None = None
    asset_id: str | None = None
    output_manifest_json: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class JobTransition:
    job_id: str
    from_status: JobStatus
    to_status: JobStatus
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None
