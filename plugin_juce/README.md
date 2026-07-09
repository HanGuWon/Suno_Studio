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
- Manual results import (`POST /jobs/{id}/manual-complete`) for requested + pending families only
- Restart-safe reconnect using persisted `lastActiveJobId` + `GET /jobs/{id}` rehydration
- Restore warnings surfaced in status text after reconnect
- Reveal / drag-copy output path (preview currently disabled)

## Build

```bash
cmake -S plugin_juce -B build/plugin_juce
cmake --build build/plugin_juce --target bridge_client
cmake --build build/plugin_juce --target SunoStudioBridgeStandalone
cmake --build build/plugin_juce --target SunoStudioBridgePlugin
cmake --build build/plugin_juce --target BridgeContractVectors
```

If JUCE is already installed, pass `-Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE`.
Otherwise CMake fetches the pinned JUCE tag from GitHub. Use
`-DSUNO_STUDIO_FETCH_JUCE=OFF` to require a local JUCE package.

On Windows, run CMake from a Visual Studio x64 developer shell or call
`vcvars64.bat` before configuring with Ninja.

## Scope limits

- No real Suno browser/session automation.
- No universal DAW auto-insert claims.
- REAPER remains assisted/manual path.
