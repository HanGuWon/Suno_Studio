"""Canonical bridge error schema helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BridgeError(Exception):
    """Bridge protocol error with stable machine-readable code."""

    code: str
    message: str
    details: dict[str, Any]
    request_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": self.request_id,
            }
        }


def make_error(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return canonical error payload."""
    return BridgeError(
        code=code,
        message=message,
        details=details or {},
        request_id=request_id,
    ).to_payload()
