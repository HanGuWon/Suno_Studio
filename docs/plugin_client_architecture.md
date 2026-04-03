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

## Persistence additions

State now includes provider mode, requested output families, handoff paths, last imported family map, mode/BPM/key/loop options, active job id, and selected output path.

## Honest scope

- No scraping/session automation.
- No ARA runtime in this milestone.
- No universal DAW timeline auto-insert.
