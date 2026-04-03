# Provider Contract

## Modes

- `mock_suno` (default): async remote-like lifecycle.
- `manual_suno`: prepares a manual handoff package, then waits for explicit manual completion intake.
- `official_api`, `web_session`: placeholders only.

Provider mode is persisted per job.

## Manual provider states

- `awaiting_manual_provider_submission`
- `awaiting_manual_provider_result`
- `importing_provider_result`

## Endpoints

- `POST /jobs/text` with optional `providerMode`.
- `POST /jobs/audio` with optional `providerMode` form field.
- `GET /jobs/{job_id}/handoff` for manual jobs.
- `POST /jobs/{job_id}/manual-complete` for manual jobs.

## Manual handoff package

`storage/provider_workspaces/<job_id>/`

- `handoff.json` (requested deliverables + mode/options)
- `prompt.txt`
- `metadata.json`
- `source_audio/` (optional)
- `README.md` (exact user instructions)

## Manual completion manifest

Bridge records:
- requested deliverables
- imported deliverables grouped by family (`mix`, `stems`, `tempoLockedStems`, `midi`)
- concrete imported file paths

No assumption is made that all requested outputs are returned.
