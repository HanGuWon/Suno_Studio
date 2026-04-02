# Plugin client architecture (phase: thin shell)

## Scope of this phase

Implemented:
- JUCE scaffold for plugin + standalone targets.
- Shared C++ bridge client layer.
- UX contract shell for text create, manual audio import, status polling, preview/drag intent.
- Host capability mode communication: generic drag, REAPER assisted, ARA planned.

Not implemented in this phase:
- Real Suno automation.
- Universal DAW auto-insert.
- Full ARA runtime.

## Layers

1. **UI layer** (plugin editor / standalone window)
2. **Bridge client layer** (`BridgeDiscovery`, `BridgeHttpClient`)
3. **State layer** (`PluginStateStore`)
4. **Host handoff layer**
   - generic drag/export workflow
   - REAPER script proof-of-concept

## Source-of-truth backend

The plugin client uses the async Python bridge runtime as source of truth for job lifecycle and assets.


## Auth/signing note

The C++ scaffold emits the same auth header names used by the Python bridge runtime (`X-Signature-*`, `X-Body-Sha256`). It is suitable for client UX integration testing with the mock backend, but should be hardened and byte-for-byte aligned with Python signer semantics before production release.
