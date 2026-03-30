# Suno Studio — Local Bridge MVP

This repository now contains a runnable **Python local bridge MVP** for Suno Studio workflows.

## What is implemented

- FastAPI bridge service bound to loopback by default (`127.0.0.1`).
- Typed HTTP endpoints:
  - `GET /capabilities`
  - `POST /jobs/text`
  - `POST /jobs/audio`
  - `GET /jobs/{job_id}`
  - `POST /jobs/{job_id}/cancel`
  - `POST /assets/import`
- Protocol compatibility middleware (`X-Protocol-Version`, etc.).
- Local security model with request signing (HMAC) enabled by default.
- Durable SQLite persistence for:
  - jobs
  - transitions
  - remote provider IDs
  - imported manifests
  - downloaded output dedup records
- Audio asset import pipeline:
  - stores original upload
  - generates manifest JSON
  - validates manifest shape against required schema keys
  - optional normalized derivative (currently placeholder copy behavior)
- Provider adapter abstraction with deterministic `MockSunoAdapter`.
- End-to-end integration tests covering text/audio flows and persistence/recovery behaviors.

## What is intentionally stubbed

- **No real Suno integration yet** (mock provider only).
- **No browser automation adapter implementation** yet.
- **No JUCE/C++ plugin runtime integration** in this step.
- **No DAW auto-insert implementation** beyond advisory capability scaffolding.
- Normalization derivative is currently non-destructive placeholder copy (documented in code).

## Local run

### 1) Install dependencies

```bash
python -m pip install -e .
```

### 2) Run bridge

```bash
suno-bridge
```

Equivalent:

```bash
python -m bridge.main
```

### 3) Optional env vars

- `BRIDGE_HOST` (default `127.0.0.1`)
- `BRIDGE_PORT` (default `7071`)
- `BRIDGE_DB_PATH` (default `storage/jobs.db`)
- `BRIDGE_ASSETS_ROOT` (default `storage/assets`)
- `BRIDGE_ENABLE_HMAC` (`1` by default)
- `BRIDGE_SHARED_SECRET` (default `dev-shared-secret`)

## Tests

```bash
pytest -q
```

Integration tests cover:

- idempotent duplicate create (`clientRequestId`)
- audio import manifest creation
- text job flow through mock adapter
- audio job flow through mock adapter
- recovery of in-flight jobs
- protocol mismatch failures
- canonical error payload shape
- downloaded asset deduplication

## Current limitations

- Mock outputs are deterministic fake bytes, not generated music.
- Recovery currently resumes by deterministic re-run of mock pipeline.
- HMAC uses shared-secret env default suitable for local MVP only.

## Recommended next step

Implement a **real asynchronous orchestration worker** (queue + background polling loop + cancellation tokens) while keeping the current API and storage contracts stable.
