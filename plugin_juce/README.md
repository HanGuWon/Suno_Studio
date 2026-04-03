# plugin_juce

Thin JUCE client layer on top of the async Python bridge.

## Included targets

- `SunoStudioBridgePlugin` (VST3/AU scaffold)
- `SunoStudioBridgeStandalone` (primary debug surface in this phase)
- shared static lib: `bridge_client`

## Shared client responsibilities

- lockfile discovery support
- dev-mode explicit endpoint support
- protocol handshake (`/capabilities`)
- HMAC header envelope emission
- JSON + multipart bridge calls
- canonical error parsing
- state persistence

## Important limitations

- JUCE keychain integration for shared-secret retrieval is not complete.
  - discovery mode can still use manual shared-secret override.
- This phase does not include real Suno automation.
- This phase does not include universal DAW auto-insert or full ARA runtime.

## Build

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce
```
