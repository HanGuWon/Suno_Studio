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

The JUCE plugin and standalone share one client surface with:

- provider selector (`mock_suno` / `manual_suno`)
- mode selector (`Song`, `Sound`, `Audio Prompt`)
- requested output families (`mix`, `stems`, `tempo-locked stems`, `MIDI`)
- sound fields (one-shot/loop, BPM, key)
- handoff actions (`Prepare/Fetch`, `Reveal`, `Open instructions`)
- manual result import (`manual-complete` endpoint)
- restart-safe reconnect restore (rehydrates active job + outputs from `/jobs/{id}`)

Preview is intentionally disabled for now (no fake playback claims in plugin/standalone); use reveal/open externally.

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
cmake --build build/plugin_juce --target BridgeContractVectors
```

## Tests

```bash
pytest -q
./build/plugin_juce/BridgeContractVectors
```

If JUCE is unavailable, C++ binaries may not build in this environment.
