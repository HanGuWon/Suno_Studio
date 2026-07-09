# Security model (current phase)

## Implemented

- Loopback bridge runtime.
- Required protocol/request headers.
- HMAC signed request envelope with replay/expiry checks.
- Local discovery/dev configuration model.

## Compliance-first provider boundary

For Suno integration in this phase, the project supports only **manual user actions** in official Suno UI.

Local drag/drop and Downloads folder scan/watch are user-driven file transfer
features. They operate only on local files visible to the user and stage files
for explicit confirmation before import.

Not implemented:
- scraping/robots
- browser automation
- reverse engineered or unofficial API wrappers
- session/cookie theft

## User notices

Client UX should remind users:
- they must have rights to uploaded source content,
- Suno ownership/commercial terms depend on their Suno plan.

This repo does not provide legal advice.
