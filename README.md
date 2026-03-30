# Suno Studio bridge + plugin persistence scaffold

This repository implements the requested behavior for bridge API/models and plugin session recovery:

- `clientRequestId` UUID on job creation payloads for text/audio.
- idempotent create semantics by `(job_type, clientRequestId)`.
- durable persistence for jobs, transitions, remote provider IDs, and downloaded assets.
- startup recovery worker for in-flight jobs.
- download dedup using `jobId + variant + checksum`.
- plugin-side persisted per-submission request IDs and reconnect reconciliation.

See tests in `tests/test_bridge.py`.
