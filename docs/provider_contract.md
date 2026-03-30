# Provider Contract

This document defines the provider-facing contract for bridge-compatible plug-ins.

## 1) Transport, Authentication, and Startup Discovery

### Transport
Providers MUST expose one of the following transports:

1. HTTP on loopback: `http://127.0.0.1:<port>`
2. gRPC on loopback: `127.0.0.1:<port>`

HTTP is the baseline requirement. gRPC MAY be offered in addition.

### Authentication model
The default model is local-process trust (loopback only). If auth is enabled, providers MUST accept a static bearer token configured at startup (`Authorization: Bearer <token>`).

### Startup discovery
Plug-ins discover the provider endpoint in this order:

1. Explicit runtime configuration (CLI/env)
2. Provider-written discovery file (JSON) containing host/port/transport
3. Built-in default (`http://127.0.0.1:7000`)

Before first job submission, plug-ins MUST call the capability handshake endpoint and validate protocol compatibility.

## 2) Required Headers

Every request from plug-in to bridge/provider MUST include:

- `X-Plugin-Version`: semantic version for the plug-in build (example: `2.4.1`)
- `X-Protocol-Version`: semantic version used by this request (example: `1.3`)
- `X-Request-ID`: unique, opaque request ID for tracing

For gRPC, use metadata keys with the same names.

## 3) Version Handshake Endpoint

`GET /capabilities` MUST return provider capabilities and supported protocol range.

### Response shape

```json
{
  "provider": "bridge",
  "provider_version": "3.2.0",
  "protocol": {
    "min_supported": "1.2",
    "max_supported": "1.3",
    "recommended": "1.3"
  },
  "features": ["submit_job", "cancel_job"]
}
```

## 4) Compatibility Policy

Providers MUST support protocol major `N` and `N-1` at minimum for rolling upgrades.

- If client protocol is within `[min_supported, max_supported]`, request proceeds.
- If lower than `min_supported`, fail with upgrade guidance.
- If higher than `max_supported`, fail with downgrade/provider-upgrade guidance.

Outside the range, the provider MUST hard-fail with a canonical error payload.

## 5) Canonical Error Schema

All non-2xx responses MUST use the canonical schema:

```json
{
  "error": {
    "code": "PROTOCOL_VERSION_UNSUPPORTED",
    "message": "Protocol 1.1 is not supported. Supported range is 1.2-1.3.",
    "details": {
      "requested": "1.1",
      "min_supported": "1.2",
      "max_supported": "1.3",
      "action": "Upgrade plugin protocol to >=1.2"
    },
    "request_id": "d793f2b0-..."
  }
}
```

### Stable error codes

- `PROTOCOL_VERSION_MISSING`
- `PROTOCOL_VERSION_INVALID`
- `PROTOCOL_VERSION_UNSUPPORTED`
- `PLUGIN_VERSION_MISSING`
- `REQUEST_ID_MISSING`
- `AUTH_REQUIRED`
- `AUTH_INVALID`
- `INTERNAL_ERROR`

Codes are stable and machine-readable; clients SHOULD branch on `error.code`, not message text.
