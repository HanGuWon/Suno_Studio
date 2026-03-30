"""Bridge-side protocol validation middleware."""

from __future__ import annotations

from dataclasses import dataclass

from bridge.errors import make_error


@dataclass(frozen=True)
class ProtocolRange:
    min_supported: str
    max_supported: str


def _parse_version(value: str) -> tuple[int, ...]:
    if not value or any(part == "" for part in value.split(".")):
        raise ValueError("invalid version")
    return tuple(int(part) for part in value.split("."))


def validate_protocol_headers(
    headers: dict[str, str],
    protocol_range: ProtocolRange,
) -> tuple[bool, dict | None]:
    """Validate required headers and protocol compatibility."""
    request_id = headers.get("X-Request-ID")
    plugin_version = headers.get("X-Plugin-Version")
    requested = headers.get("X-Protocol-Version")

    if not request_id:
        return False, make_error(
            "REQUEST_ID_MISSING",
            "Missing required header X-Request-ID.",
        )

    if not plugin_version:
        return False, make_error(
            "PLUGIN_VERSION_MISSING",
            "Missing required header X-Plugin-Version.",
            request_id=request_id,
        )

    if not requested:
        return False, make_error(
            "PROTOCOL_VERSION_MISSING",
            "Missing required header X-Protocol-Version.",
            request_id=request_id,
        )

    try:
        req_v = _parse_version(requested)
        min_v = _parse_version(protocol_range.min_supported)
        max_v = _parse_version(protocol_range.max_supported)
    except ValueError:
        return False, make_error(
            "PROTOCOL_VERSION_INVALID",
            f"Invalid protocol version '{requested}'. Use semantic version format.",
            details={"requested": requested},
            request_id=request_id,
        )

    if req_v < min_v:
        return False, make_error(
            "PROTOCOL_VERSION_UNSUPPORTED",
            (
                f"Protocol {requested} is too old. "
                f"Supported range is {protocol_range.min_supported}-{protocol_range.max_supported}."
            ),
            details={
                "requested": requested,
                "min_supported": protocol_range.min_supported,
                "max_supported": protocol_range.max_supported,
                "action": f"Upgrade plugin protocol to >={protocol_range.min_supported}",
            },
            request_id=request_id,
        )

    if req_v > max_v:
        return False, make_error(
            "PROTOCOL_VERSION_UNSUPPORTED",
            (
                f"Protocol {requested} is newer than provider support. "
                f"Supported range is {protocol_range.min_supported}-{protocol_range.max_supported}."
            ),
            details={
                "requested": requested,
                "min_supported": protocol_range.min_supported,
                "max_supported": protocol_range.max_supported,
                "action": (
                    f"Downgrade plugin protocol to <={protocol_range.max_supported} "
                    "or upgrade provider"
                ),
            },
            request_id=request_id,
        )

    return True, None
