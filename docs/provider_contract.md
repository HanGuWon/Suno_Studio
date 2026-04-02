# Provider Contract (Bridge Runtime Baseline)

This document defines the current bridge contract used by plugin/standalone clients in this repository.

## Transport and discovery

- Transport: HTTP loopback only (`http://127.0.0.1:<port>`).
- Discovery order:
  1. explicit dev config (host/port/secret)
  2. bridge lockfile discovery
  3. default dev fallback (`127.0.0.1:7071`)

## Auth model (current baseline)

Plugin/standalone clients sign requests with HMAC-SHA256 headers:

- `X-Signature-Timestamp`
- `X-Signature-Nonce`
- `X-Body-Sha256`
- `X-Signature`

Signature formula:

`signature = HMAC_SHA256(shared_secret, "{timestamp}.{nonce}.{body_sha256}")`

No bearer-token baseline is used for plugin↔bridge in this phase.

## Required headers

All requests include:

- `X-Plugin-Version`
- `X-Protocol-Version`
- `X-Request-ID`

## Handshake

Clients call `GET /capabilities` before first job submission and enforce protocol range checks.

## Endpoint contract used by client layer

- `GET /capabilities`
- `POST /jobs/text` (JSON)
- `POST /assets/import` (multipart/form-data)
- `POST /jobs/audio` (multipart/form-data)
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`

## Canonical error payload

```json
{
  "error": {
    "code": "PROTOCOL_VERSION_UNSUPPORTED",
    "message": "...",
    "details": {},
    "request_id": "..."
  }
}
```

Clients should branch on `error.code`, not free-form message text.
