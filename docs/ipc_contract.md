# IPC Contract (Current Bridge↔Client)

## Protocol

- Client MUST send `X-Plugin-Version`, `X-Protocol-Version`, `X-Request-ID`.
- Client SHOULD call `GET /capabilities` before job submission.
- Client MUST reject unsupported protocol ranges from handshake response.

## Auth envelope

For signed requests (current baseline):

- `X-Signature-Timestamp`
- `X-Signature-Nonce`
- `X-Body-Sha256`
- `X-Signature`

Where:
- `body_sha256 = SHA256(request_body_bytes)`
- `signature = HMAC_SHA256(secret, "{timestamp}.{nonce}.{body_sha256}")`

## Payload types

- `/jobs/text`: JSON
- `/assets/import`: multipart/form-data
- `/jobs/audio`: multipart/form-data

## Response expectations

- Success responses are endpoint-specific JSON objects.
- Non-2xx responses should follow canonical error schema.

## Canonical error schema

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": {},
    "request_id": "..."
  }
}
```
