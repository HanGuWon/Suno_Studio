"""Bridge protocol helper responses."""

from __future__ import annotations


def capabilities_payload(
    *,
    provider_version: str,
    min_supported: str,
    max_supported: str,
    recommended: str | None = None,
) -> dict:
    return {
        "provider": "bridge",
        "provider_version": provider_version,
        "protocol": {
            "min_supported": min_supported,
            "max_supported": max_supported,
            "recommended": recommended or max_supported,
        },
    }
