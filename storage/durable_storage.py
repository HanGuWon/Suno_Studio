from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

from bridge.models import IN_FLIGHT_STATES, Job, JobStatus, JobTransition, JobType


class DurableStorage:
    """SQLite-backed durable storage for jobs/transitions/assets."""

    def __init__(self, db_path: str | Path = "storage/jobs.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    client_request_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    remote_provider_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(type, client_request_id)
                );

                CREATE TABLE IF NOT EXISTS job_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    reason TEXT,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS downloaded_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(job_id, variant, checksum)
                );
                """
            )

    def get_job_by_request_id(self, job_type: JobType, client_request_id: UUID) -> Job | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE type = ? AND client_request_id = ?",
                (job_type.value, str(client_request_id)),
            ).fetchone()
            return _row_to_job(row) if row else None

    def create_job(self, job: Job) -> Job:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, type, status, client_request_id, payload_json, remote_provider_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.type.value,
                    job.status.value,
                    str(job.client_request_id),
                    json.dumps(job.payload),
                    job.remote_provider_id,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
            return job

    def set_job_status(
        self,
        job_id: str,
        to_status: JobStatus,
        *,
        reason: str | None = None,
        remote_provider_id: str | None = None,
    ) -> Job:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown job_id={job_id}")
            current = _row_to_job(row)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE jobs SET status = ?, remote_provider_id = COALESCE(?, remote_provider_id), updated_at = ? WHERE id = ?",
                (to_status.value, remote_provider_id, now, job_id),
            )
            transition = JobTransition(job_id=job_id, from_status=current.status, to_status=to_status, reason=reason)
            conn.execute(
                "INSERT INTO job_transitions (job_id, from_status, to_status, occurred_at, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    transition.job_id,
                    transition.from_status.value,
                    transition.to_status.value,
                    transition.occurred_at.isoformat(),
                    transition.reason,
                ),
            )
            refreshed = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return _row_to_job(refreshed)

    def list_in_flight_jobs(self) -> list[Job]:
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status IN ({','.join('?' for _ in IN_FLIGHT_STATES)})",
                tuple(status.value for status in IN_FLIGHT_STATES),
            ).fetchall()
            return [_row_to_job(row) for row in rows]

    def record_downloaded_asset(self, *, job_id: str, variant: str, checksum: str, local_path: str) -> bool:
        """Returns True if inserted, False if duplicate."""
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO downloaded_assets (job_id, variant, checksum, local_path, created_at) VALUES (?, ?, ?, ?, ?)",
                    (job_id, variant, checksum, local_path, datetime.now(timezone.utc).isoformat()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_jobs_by_ids(self, job_ids: list[str]) -> list[Job]:
        if not job_ids:
            return []
        placeholders = ",".join("?" for _ in job_ids)
        with self._conn() as conn:
            rows = conn.execute(f"SELECT * FROM jobs WHERE id IN ({placeholders})", tuple(job_ids)).fetchall()
            return [_row_to_job(row) for row in rows]


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        type=JobType(row["type"]),
        status=JobStatus(row["status"]),
        client_request_id=UUID(row["client_request_id"]),
        payload=json.loads(row["payload_json"]),
        remote_provider_id=row["remote_provider_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
