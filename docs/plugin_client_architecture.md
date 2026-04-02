# Plugin client architecture (client-convergence phase)

## Implemented in this phase

- Shared C++ `BridgeController` used by both plugin editor and standalone app.
- Shared `BridgeHttpClient` with handshake, HMAC headers, JSON + multipart endpoint handling.
- Shared `PluginStateStore` persistence for recent jobs/assets and last output context.
- Generic drag/reveal/preview output workflow.
- REAPER-assisted manual adapter path documented separately.

## Layering

1. **Controller layer** (`BridgeController`)
   - connect/disconnect
   - submit text/audio
   - poll/cancel
   - output selection
   - persistence updates
2. **Transport layer** (`BridgeHttpClient`)
   - discovery/dev endpoint targeting
   - header/signing envelope
   - endpoint calls and canonical error parsing
3. **State layer** (`PluginStateStore`)
   - persisted UX/session continuity
4. **UI surfaces**
   - plugin editor
   - standalone app

## Auth/signing status

The client emits the same signature header shape as Python bridge runtime and follows the same payload pattern for request signing.

## Honest limitations

- Full production keychain bootstrap on JUCE side is not complete yet.
- Manual shared-secret override is still supported for practical local development.
- ARA runtime remains future work.
