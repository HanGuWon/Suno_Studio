# Suno Studio — Async Local Bridge Runtime

This repository contains a runnable **asynchronous Python local bridge** for Suno Studio workflows.

## What is implemented now

- FastAPI bridge service with stable endpoint paths:
  - `GET /capabilities`
  - `POST /jobs/text`
  - `POST /jobs/audio`
  - `GET /jobs/{job_id}`
  - `POST /jobs/{job_id}/cancel`
  - `POST /assets/import`
- Background async-style orchestration runtime (threaded worker loop + queue) so job creation requests return quickly.
- Durable SQLite persistence for job lifecycle, progress, remote IDs, artifacts, transitions, and asset manifests.
- Restart-safe recovery that re-enqueues non-terminal jobs and avoids duplicate output writes via checksum dedup.
- Protocol compatibility middleware and HMAC request verification.
- Deterministic `MockSunoAdapter` that simulates queued/in-progress/ready states plus cancellation and retryable failures.
- Asset import/manifest pipeline with preserved originals and optional placeholder normalized derivative.

## Async runtime behavior

- `POST /jobs/text` and `POST /jobs/audio` create jobs and enqueue orchestration work.
- Worker transitions jobs through states such as `queued_local`, `submitting_remote`, `polling_remote`, `downloading`, then terminal states.
- `GET /jobs/{job_id}` returns the latest persisted status with progress fields:
  - `status`, `progress`, `remoteJobId`, `lastError`, `outputAssets`.
- Cancellation can race with execution safely and results in stable terminal outcome (`cancelled` or already `complete`).

## Runtime bootstrap & discovery

- **Dev mode** (`BRIDGE_DEV_MODE=1`): fixed host/port/env secret.
- **Normal mode**: loopback-only host + random port, lockfile discovery, keychain-backed shared-secret bootstrap metadata.
- Discovery lockfile defaults to `~/.suno_studio/bridge.lock` and includes host/port/protocol/auth bootstrap hints.

## What is intentionally still stubbed

- No real Suno provider integration yet.
- No browser automation implementation.
- No JUCE/VST3/AU runtime integration in this step.
- No real DAW auto-insert logic.
- No real audio loudness normalization DSP (placeholder derivative only).

## Run locally

```bash
python -m pip install -e .
python -m bridge.main
```

Optional environment variables:

- `BRIDGE_DEV_MODE` (`1` for fixed local settings)
- `BRIDGE_HOST`, `BRIDGE_PORT`
- `BRIDGE_DB_PATH`, `BRIDGE_ASSETS_ROOT`
- `BRIDGE_ENABLE_HMAC`
- `BRIDGE_SHARED_SECRET`
- `BRIDGE_LOCKFILE`

## Tests

```bash
pytest -q
```

Integration tests cover non-blocking job creation, polling to completion, cancellation scenarios, restart recovery, concurrent idempotency, dedup after restart, protocol mismatch behavior, and signed request behavior.

## Why JUCE/plugin integration is deferred

This step hardens bridge runtime semantics (async orchestration, cancellation, recovery, bootstrap/security). Plugin integration should start after these runtime contracts are stable.

## Exact next recommended step

Add a persisted remote-poll scheduler with per-job backoff jitter and provider-specific retry classification, then wire a first non-mock provider adapter behind the same orchestrator contract.
