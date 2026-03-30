# IPC Contract

This IPC contract is normative for bridge and plug-in interoperability.

## Transport

- Supported transport: `http://127.0.0.1:<port>` (required), gRPC (optional).
- Startup discovery priority:
  1. Explicit config/env override
  2. Discovery file
  3. Default endpoint

## Request metadata

Required metadata for every call:

- `X-Plugin-Version` (required)
- `X-Protocol-Version` (required)
- `X-Request-ID` (required)

## Handshake

Clients MUST call `GET /capabilities` before first `submit_job` request.

### Example

```http
GET /capabilities HTTP/1.1
Host: 127.0.0.1:7000
X-Plugin-Version: 2.4.1
X-Protocol-Version: 1.3
X-Request-ID: 5ea63e45-5718-47f5-a9a8-d1dc2154c29a
```

```json
{
  "provider": "bridge",
  "provider_version": "3.2.0",
  "protocol": {
    "min_supported": "1.2",
    "max_supported": "1.3",
    "recommended": "1.3"
  }
}
```

## Compatibility policy

- Runtime policy: support protocol major `N` and `N-1`.
- Hard-fail any request outside the negotiated range.
- Error payloads MUST follow the canonical schema.

## Canonical error schema

```json
{
  "error": {
    "code": "PROTOCOL_VERSION_UNSUPPORTED",
    "message": "Requested protocol is outside supported range.",
    "details": {
      "requested": "1.4",
      "min_supported": "1.2",
      "max_supported": "1.3",
      "action": "Downgrade plugin protocol to <=1.3 or upgrade provider"
    },
    "request_id": "5ea63e45-5718-47f5-a9a8-d1dc2154c29a"
  }
}
```

## Error codes

Stable machine-readable codes:

- `PROTOCOL_VERSION_MISSING`
- `PROTOCOL_VERSION_INVALID`
- `PROTOCOL_VERSION_UNSUPPORTED`
- `PLUGIN_VERSION_MISSING`
- `REQUEST_ID_MISSING`
- `AUTH_REQUIRED`
- `AUTH_INVALID`
- `INTERNAL_ERROR`
