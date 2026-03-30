from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from bridge.models import IN_FLIGHT_STATES, Job, JobStatus, JobTransition, JobType


_ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.SUBMITTED, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.SUBMITTED: {JobStatus.POLLING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.POLLING: {JobStatus.DOWNLOADING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.DOWNLOADING: {JobStatus.COMPLETE, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.COMPLETE: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.FAILED: set(),
}


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
                    asset_id TEXT,
                    output_manifest_json TEXT,
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

                CREATE TABLE IF NOT EXISTS imported_assets (
                    id TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "asset_id" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN asset_id TEXT")
            if "output_manifest_json" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN output_manifest_json TEXT")

    def get_job_by_request_id(self, job_type: JobType, client_request_id: UUID) -> Job | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE type = ? AND client_request_id = ?",
                (job_type.value, str(client_request_id)),
            ).fetchone()
            return _row_to_job(row) if row else None

    def get_job(self, job_id: str) -> Job | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return _row_to_job(row) if row else None

    def get_imported_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM imported_assets WHERE id = ?",
                (asset_id,),
            ).fetchone()
            return json.loads(row["manifest_json"]) if row else None

    def create_job(self, job: Job) -> Job:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, type, status, client_request_id, payload_json, remote_provider_id,
                    asset_id, output_manifest_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.type.value,
                    job.status.value,
                    str(job.client_request_id),
                    json.dumps(job.payload),
                    job.remote_provider_id,
                    job.asset_id,
                    json.dumps(job.output_manifest_json) if job.output_manifest_json else None,
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
            if to_status not in _ALLOWED_TRANSITIONS[current.status] and current.status != to_status:
                raise ValueError(f"Invalid transition {current.status.value} -> {to_status.value}")
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

    def attach_job_artifacts(
        self,
        job_id: str,
        *,
        asset_id: str | None = None,
        output_manifest: dict[str, Any] | None = None,
    ) -> Job:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown job_id={job_id}")
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE jobs
                SET asset_id = COALESCE(?, asset_id),
                    output_manifest_json = COALESCE(?, output_manifest_json),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    asset_id,
                    json.dumps(output_manifest) if output_manifest else None,
                    now,
                    job_id,
                ),
            )
            refreshed = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return _row_to_job(refreshed)

    def save_imported_asset(self, asset_id: str, manifest: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO imported_assets (id, manifest_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET manifest_json=excluded.manifest_json
                """,
                (
                    asset_id,
                    json.dumps(manifest),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

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
        asset_id=row["asset_id"],
        output_manifest_json=json.loads(row["output_manifest_json"]) if row["output_manifest_json"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
