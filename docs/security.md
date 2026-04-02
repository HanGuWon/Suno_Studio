# Bridge Security Model (Current Phase)

## Baseline assumptions

- Bridge listens on loopback only.
- Plugin/standalone client is same-user local process.
- Shared secret is required for HMAC request signing.

## Implemented plugin↔bridge controls

1. Required protocol/request headers:
   - `X-Plugin-Version`, `X-Protocol-Version`, `X-Request-ID`
2. HMAC request envelope:
   - `X-Signature-Timestamp`, `X-Signature-Nonce`, `X-Body-Sha256`, `X-Signature`
3. Replay/expiry checks enforced by bridge signer logic.
4. Discovery lockfile path and protocol/auth metadata for runtime endpoint discovery.

## Current-phase practical bootstrap

Two supported client modes:

- **Discovery mode**: read lockfile host/port/protocol and use shared-secret override if needed.
- **Dev mode**: explicit host/port/shared-secret config.

If keychain retrieval is not wired on the JUCE side yet, manual secret override is allowed and must be documented.

## Out of scope for this phase

- Real provider auth/session automation.
- Remote network trust models.
- ARA-specific security hardening.
