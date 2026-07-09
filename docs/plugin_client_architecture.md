# Plugin client architecture

## Layering

1. `BridgeModels`: provider mode, client mode, requested output families, handoff/state parsing helpers.
2. `BridgeHttpClient`: HMAC handshake envelope + JSON/multipart endpoints including manual-provider endpoints.
3. `BridgeController`: non-UI orchestration for both plugin and standalone.
4. `PluginStateStore`: persisted manual-mode and output-selection context.
5. `BridgeClientSurface`: shared JUCE component used by plugin editor and standalone app.

## Manual-provider convergence

The C++ client now directly supports the existing bridge contract:

- submit with `providerMode` on text/audio
- request output families through metadata flags
- fetch manual handoff package (`/jobs/{id}/handoff`)
- import manual result files by family (`/jobs/{id}/manual-complete`)
- render waiting states (`awaiting_manual_provider_submission`, `awaiting_manual_provider_result`, `importing_provider_result`)
- surface reconnect restore warnings in shared UI status text instead of silently swallowing them

## Persistence additions

State now includes provider mode, requested output families, handoff paths, last imported family map, mode/BPM/key/loop options, active job id, and selected output path.

Persisted job state is treated as a pointer only: on reconnect the client re-fetches `GET /jobs/{id}` for `lastActiveJobId` and rehydrates active job data, outputs, manual waiting state, and handoff metadata when available.

Manual import prompting is manifest-aware: when `requestedDeliverables` is present, the shared surface asks only for requested + not-yet-imported families and skips `/manual-complete` entirely if no files were selected.

## Drop intake

`BridgeClientSurface` accepts local audio/MIDI file drops. For active `manual_suno`
jobs that are waiting for result files, dropped files are staged first instead of
immediately uploaded. The UI shows a small confirmation row:

- dropped file count and first filename
- inferred result family
- editable family selector
- import and clear actions

This supports one-family-at-a-time correction while keeping the transfer user-driven.
The bridge also appends later manual-complete imports to the existing manifest so
users can import mix, stems, tempo-locked stems, and MIDI in separate passes.

## Preview semantics

Preview is explicitly disabled in the shared JUCE surface for this milestone. The UI keeps reveal/drag-copy actions only, and does not claim plugin-editor playback support without a real host-safe playback path.

## Honest scope

- No scraping/session automation.
- No ARA runtime in this milestone.
- No universal DAW timeline auto-insert.
