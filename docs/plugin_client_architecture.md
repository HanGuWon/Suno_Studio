# Plugin client architecture

## Layering

1. `BridgeModels`: provider mode, client mode, requested output families, handoff/state parsing helpers.
2. `BridgeHttpClient`: HMAC handshake envelope + JSON/multipart endpoints including manual-provider endpoints.
3. `BridgeController`: non-UI orchestration for both plugin and standalone.
4. `PluginStateStore`: persisted pointers/manual-mode/output-selection context.
5. `BridgeClientSurface`: shared JUCE component used by plugin editor and standalone app.

## Restart-safe behavior

Persisted state is a pointer, not source-of-truth job state.

On reconnect the controller attempts to rehydrate from bridge APIs:

- load `lastActiveJobId`
- call `GET /jobs/{id}`
- repopulate active job + outputs + manual waiting state
- attempt `GET /jobs/{id}/handoff` for manual jobs

## Manual-provider convergence

The C++ client directly supports the existing bridge contract:

- submit with `providerMode` on text/audio
- request output families through metadata flags
- fetch manual handoff package (`/jobs/{id}/handoff`)
- import manual result files by family (`/jobs/{id}/manual-complete`)
- render waiting states (`awaiting_manual_provider_submission`, `awaiting_manual_provider_result`, `importing_provider_result`)

## Persistence additions

State includes provider mode, requested output families, handoff paths, last imported family map, mode/BPM/key/loop options, active job id, and selected output path.

## Honest UX constraints

- Preview is disabled in this milestone (no fake playback path claims).
- Poll/connect/handoff/action errors are surfaced in the shared surface status text.

## Honest scope

- No scraping/session automation.
- No ARA runtime in this milestone.
- No universal DAW timeline auto-insert.
