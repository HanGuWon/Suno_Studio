# plugin_juce scaffold

This folder contains the first thin JUCE client scaffold for the async bridge runtime.

## What is implemented

- Shared C++ bridge client layer (`BridgeDiscovery`, `BridgeHttpClient`, `PluginStateStore`).
- JUCE plugin shell targets (VST3 + AU) and a standalone GUI app target.
- UI contract shell for connection, create, audio import, job status, preview, and drag export.

## What is not implemented yet

- Full polished JUCE UX and production visuals.
- Real Suno provider automation.
- Universal DAW auto-insert.
- ARA runtime.

## Build prerequisites

- CMake 3.22+
- C++17 compiler
- JUCE provided externally (not vendored in this repo)

Example configure:

```bash
cmake -S plugin_juce -B build/plugin_juce -Djuce_DIR=/path/to/JUCE/lib/cmake/JUCE
cmake --build build/plugin_juce
```

If AU target is not available in your environment, VST3/standalone remain the intended debug path.
