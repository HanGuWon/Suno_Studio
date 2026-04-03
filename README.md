# Suno Studio — Async Bridge with Mock + Manual Suno Provider Modes

This repo provides:

1. Async Python bridge runtime (source of truth).
2. Mock provider automation path for deterministic tests/dev.
3. Compliance-first **manual_suno** path for real human-in-the-loop Suno workflows.
4. JUCE plugin + standalone shell for submit/poll/import/preview/reveal/drag handoff.

## Provider modes

- `mock_suno` (default): bridge worker submits/polls/downloads automatically.
- `manual_suno`: bridge prepares a handoff package and waits for user completion.
- placeholders only: `official_api`, `web_session`.

Each job persists its `providerMode` and provider metadata.

## Manual Suno workflow (no automation)

1. Submit text or audio job with `providerMode=manual_suno`.
2. Bridge prepares `storage/provider_workspaces/<job_id>/` with:
   - `handoff.json`
   - `prompt.txt`
   - `metadata.json`
   - `source_audio/` (for audio prompt jobs)
   - `README.md` instructions
3. User performs the job manually in Suno UI.
4. User imports downloaded outputs via `POST /jobs/{job_id}/manual-complete`.
5. Bridge attaches imported outputs, normalizes manifest, and marks job complete.

## Bridge endpoints used now

- `GET /capabilities`
- `POST /jobs/text` (JSON)
- `POST /assets/import` (multipart)
- `POST /jobs/audio` (multipart)
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /jobs/{job_id}/handoff`
- `POST /jobs/{job_id}/manual-complete`

## Compliance boundary

This repository does **not** implement scraping, browser automation, reverse engineering, session theft, or unofficial Suno APIs.

## Build/setup

```bash
python -m pip install -e .
python -m bridge.main
```

JUCE (external):

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce
```

## Tests

```bash
npm test
pytest -q
```

## Environment note

JUCE binaries were not built in this environment.
