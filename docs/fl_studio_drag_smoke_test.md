# FL Studio drag/drop smoke test

This smoke test verifies the two practical file-transfer paths for the current beta:

1. Local Suno-download-style files dropped into the Suno Studio plugin or standalone surface.
2. Completed bridge output dragged or copied into the FL Studio Playlist.

The workflow remains user-driven. The project does not automate the Suno website or inspect browser sessions.

## Prepare assets

Create deterministic smoke files:

```bash
python tools/make_fl_studio_smoke_assets.py
```

The script writes:

- `build/fl_studio_smoke_assets/suno_mix_smoke.wav`
- `build/fl_studio_smoke_assets/suno_vocal_stem_smoke.wav`
- `build/fl_studio_smoke_assets/suno_tempo_locked_bpm120_smoke.wav`
- `build/fl_studio_smoke_assets/suno_midi_smoke.mid`

## Build client

Build the standalone or plugin target with a local JUCE install:

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce --target SunoStudioBridgeStandalone
cmake --build build/plugin_juce --target SunoStudioBridgePlugin
```

## Test Suno-style results into the client

1. Start the bridge: `uv run suno-bridge`.
2. Open the standalone app or the plugin in FL Studio.
3. Connect to the bridge.
4. Select `manual_suno`, request `mix`, `stems`, `tempo-locked stems`, and `MIDI`.
5. Submit a text job and wait for `awaiting_manual_provider_result`.
6. Drop the generated smoke files onto the client surface.
7. Confirm the job completes and output paths appear in the result selector.

Expected family routing:

- `suno_mix_smoke.wav` -> mix
- `suno_vocal_stem_smoke.wav` -> stems
- `suno_tempo_locked_bpm120_smoke.wav` -> tempo-locked stems
- `suno_midi_smoke.mid` -> MIDI

## Test client output into FL Studio

1. Select a completed output in the client result selector.
2. Use `Drag / copy result path`.
3. Drop into the FL Studio Playlist.
4. Confirm the clip lands on a Playlist track and the clipboard path still points to the same file.

## Record result

Capture:

- FL Studio version
- standalone or plugin path tested
- bridge commit SHA
- whether each family routed correctly
- whether Playlist drop succeeded
