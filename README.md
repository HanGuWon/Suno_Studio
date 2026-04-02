# Suno Studio — Async Bridge + JUCE Client Convergence

This repo currently provides:

1. Async Python bridge runtime (mock-provider backed).
2. JUCE plugin + standalone client shell wired to the bridge contract.

## Bridge source of truth

Current client implementation targets these bridge endpoints and payload types:

- `GET /capabilities` (handshake)
- `POST /jobs/text` (JSON)
- `POST /assets/import` (multipart/form-data)
- `POST /jobs/audio` (multipart/form-data)
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`

Plugin/standalone requests include protocol headers and HMAC envelope headers expected by the bridge.

## What the client can do now

- Connect to bridge (discovery mode or dev mode).
- Submit text jobs.
- Import local audio file and submit audio job.
- Poll async job status.
- Display output files.
- Preview output audio.
- Reveal output in file browser.
- Drag/copy output path for DAW handoff.

## REAPER PoC

Manual assisted scripts are provided under `host_adapters/reaper/`:
- insert generated file at cursor
- prepare export range from time selection/selected item

This is **not** universal auto-insert.

## Not implemented in this phase

- Real Suno browser/session automation
- Universal DAW timeline auto-insert
- Full ARA runtime

## Build/setup

### Python bridge

```bash
python -m pip install -e .
python -m bridge.main
```

### JUCE client

JUCE is not vendored; provide it externally.

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce
```

## Tests run

```bash
npm test
pytest -q
```

## Important build reality

- In this environment, JUCE binaries were **not** compiled.
- Bridge/client contract tests and runtime tests were run.

## Docs

- `docs/plugin_client_architecture.md`
- `docs/user_workflows.md`
- `docs/reaper_adapter.md`
- `docs/ara_plan.md`
- `docs/security.md`
- `docs/provider_contract.md`
- `docs/ipc_contract.md`
