# Suno Studio — Async Bridge + Plugin Client Shell

This repository now includes:
- Async local bridge runtime (Python/FastAPI).
- Thin JUCE plugin/standalone client scaffold for DAW-facing UX contract testing.

## Implemented now

### Async bridge runtime
- `GET /capabilities`
- `POST /jobs/text`
- `POST /jobs/audio`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `POST /assets/import`
- Background orchestration worker with durable recovery.
- HMAC/protocol middleware and canonical error structure.
- Deterministic mock provider backend.

### Plugin client shell (new)
- `plugin_juce/` CMake scaffold for:
  - VST3 plugin target
  - AU target (when supported by environment)
  - Standalone debug app target
- Shared C++ bridge client shell:
  - discovery + handshake
  - text job submission
  - asset import
  - audio job submission
  - status polling
  - cancellation
- Plugin state persistence shell (recent jobs/request IDs/asset IDs/preferences).
- REAPER proof-of-concept adapter scripts.

## What remains future work

- Real Suno provider adapter (beyond mock).
- Universal DAW auto-insert.
- Full ARA runtime integration.
- Other host-specific adapters beyond REAPER PoC.

## Generic vs host-specific behavior

### Generic (all hosts)
- Generate in plugin
- Preview
- Drag result to DAW timeline / OS

### REAPER-specific PoC
- Insert generated file at cursor via script
- Prepare export range from time selection/selected item

## Build / setup

### Python bridge
```bash
python -m pip install -e .
python -m bridge.main
```

### JUCE scaffold
JUCE is not vendored. Provide JUCE externally.

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce
```

## Tests run in this environment
- Pure logic/runtime tests only.
- JUCE binaries were **not built** in this environment.

```bash
node tests/hostCapabilityService.test.mjs
```

(Bridge Python tests may require Python 3.11+ because project metadata requires `>=3.11`.)

## Additional docs
- `docs/plugin_client_architecture.md`
- `docs/reaper_adapter.md`
- `docs/user_workflows.md`
- `docs/ara_plan.md`
