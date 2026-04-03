# Plugin client architecture

## Current layering

1. `BridgeController`: connect, submit, poll, cancel, output state.
2. `BridgeHttpClient`: protocol headers + HMAC + JSON/multipart calls.
3. `PluginStateStore`: persisted context.
4. Plugin and standalone surfaces.

## Provider-mode behavior

Client requests can select `providerMode` (`mock_suno` or `manual_suno`).

For `manual_suno` jobs, the bridge lifecycle is explicit waiting + manual completion intake rather than remote polling automation.

## Honest scope

- No Suno automation/scraping logic.
- No universal DAW auto-insert.
- No ARA runtime in this phase.
