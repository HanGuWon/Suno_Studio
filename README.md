# Suno Studio — Async Bridge with Mock + Manual Suno Provider Modes

This repo provides:

1. Async Python bridge runtime (source of truth).
2. Mock provider automation path for deterministic tests/dev.
3. Compliance-first `manual_suno` human-in-the-loop workflow.
4. JUCE plugin + standalone client with a shared manual-parity surface.

## Provider modes

- `mock_suno` (default): bridge worker submits/polls/downloads automatically.
- `manual_suno`: bridge prepares handoff workspace and waits for explicit manual import.
- placeholders only: `official_api`, `web_session`.

## Client reality in this milestone

The JUCE plugin and standalone now both expose the same shared client surface with:

- provider selector (`mock_suno` / `manual_suno`)
- mode selector (`Song`, `Sound`, `Audio Prompt`)
- requested output families (`mix`, `stems`, `tempo-locked stems`, `MIDI`)
- sound fields (one-shot/loop, BPM, key)
- restart-safe reconnect that rehydrates `lastActiveJobId` from `GET /jobs/{id}`
- handoff actions (`Prepare/Fetch`, `Reveal`, `Open instructions`)
- manual result import (`manual-complete` endpoint) for only requested + pending families, then reveal/drag/copy

Preview is intentionally disabled for now across plugin + standalone until a full playback path is implemented.

No provider automation beyond `mock_suno` is introduced.

## Bridge endpoints used now

- `GET /capabilities`
- `POST /jobs/text`
- `POST /assets/import`
- `POST /jobs/audio`
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
cmake --build build/plugin_juce --target bridge_client
cmake --build build/plugin_juce --target SunoStudioBridgeStandalone
cmake --build build/plugin_juce --target SunoStudioBridgePlugin
```

## Tests

```bash
pytest -q
cmake --build build/plugin_juce --target BridgeContractVectors
./build/plugin_juce/BridgeContractVectors
```

If JUCE is unavailable, C++ binaries may not build in this environment.
