# Bridge Security Threat Model and Controls

## Scope

This document defines the baseline security posture for local plug-in ↔ bridge communication.

## Threat model

### Assets

- Provider access tokens and refresh tokens.
- Provider session artifacts persisted under `sessions/`.
- User prompt content and generation metadata.
- Integrity of bridge commands from local plug-ins.

### Assumptions

- The bridge runs as the same OS user as the plug-in.
- The network path is local loopback only (`127.0.0.1`).
- A **local attacker** may be able to:
  - Open local TCP connections.
  - Read world-readable files and logs.
  - Replay captured local traffic.
- A local attacker is **not** assumed to have root/admin access or code execution in the bridge process.

## Implemented controls

### 1) Per-install shared secret in OS credential store

- On first run, the bridge creates a random 256-bit secret.
- The secret is persisted in the operating system credential manager:
  - macOS Keychain via `security`.
  - Linux Secret Service via `secret-tool`.
  - Windows Credential Manager registration via `cmdkey`.
- Subsequent runs load the existing secret; it is never logged.

### 2) HMAC-signed request envelope

Each plug-in request must include:

- `timestamp` (seconds).
- `nonce` (high-entropy unique value).
- `body_sha256` (payload integrity digest).
- `signature` where:

`signature = HMAC_SHA256(secret, "{timestamp}.{nonce}.{body_sha256}")`

The bridge validates:

- Timestamp skew within configured window.
- Body hash matches actual request body.
- HMAC compares in constant time.

Unsigned or malformed envelopes are rejected.

### 3) Expiration and replay protection

- Requests outside timestamp skew are rejected as expired/future.
- Nonces are cached for TTL window.
- Reused nonces are rejected as replay attempts.

### 4) Loopback-only random high-port + lockfile discovery

- Bridge binds only to `127.0.0.1`.
- Port is selected by OS random ephemeral allocation (`port=0`).
- Discovery metadata is published to a lockfile with mode `0600` and includes:
  - host, port, process id, discovery token.
- Lockfile is removed on shutdown.

### 5) Default log redaction + secure debug toggle

- Structured logs redact sensitive keys by default (token/cookie/prompt/session values).
- Full sensitive logging requires explicit opt-in:
  - `BRIDGE_SECURE_DEBUG=1`
- Default behavior is least-privilege observability.

### 6) `sessions/` encryption at rest

- Provider session artifacts are encrypted before disk write.
- Encryption keys are derived from the install shared secret.
- Ciphertext includes integrity protection (HMAC) to detect tampering.
- Files are written with restrictive permissions (`0600`), directory as `0700`.

## Residual risk

- A same-user attacker with live process memory access can still extract in-memory secrets.
- If OS credential service is unavailable/misconfigured, first-run bootstrap may fail.
- Local malware with keystroke/screen capture can exfiltrate prompts before encryption.
- Availability can be impacted by local DoS (port squatting, lockfile deletion).
- Custom cryptographic constructions carry implementation risk and should be replaced with a vetted AEAD library where feasible.

## Operational recommendations

- Rotate shared secret on suspicious local compromise.
- Keep lockfile and session directories in user-private paths.
- Disable secure debug logging in production environments.
- Periodically audit nonce cache, signature failures, and replay rejections.
