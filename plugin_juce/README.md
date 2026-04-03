# plugin_juce

JUCE client layer on top of the async Python bridge.

## Included targets

- `bridge_client` shared C++ client/controller/ui logic
- `SunoStudioBridgePlugin` (VST3/AU)
- `SunoStudioBridgeStandalone` (primary debug surface)
- `BridgeContractVectors` (pure C++ contract-vector checks)

## Shared surface parity

Plugin and standalone now both host `BridgeClientSurface`, which exposes:

- Connect / Connect Dev
- Submit text / import+submit audio
- Provider mode and output-family selection
- Manual handoff actions (`GET /jobs/{id}/handoff`)
- Manual results import (`POST /jobs/{id}/manual-complete`)
- Preview / reveal / drag-copy output path

## Build

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce --target bridge_client
cmake --build build/plugin_juce --target SunoStudioBridgeStandalone
cmake --build build/plugin_juce --target SunoStudioBridgePlugin
cmake --build build/plugin_juce --target BridgeContractVectors
```

## Scope limits

- No real Suno browser/session automation.
- No universal DAW auto-insert claims.
- REAPER remains assisted/manual path.
