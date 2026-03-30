import json
import urllib.request
from uuid import uuid4

import pytest

from bridge.client import BridgeClient, ClientConfig
from bridge.middleware import ProtocolRange, validate_protocol_headers


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_middleware_accepts_n_and_n_minus_1():
    protocol_range = ProtocolRange(min_supported="1.2", max_supported="1.3")

    headers_n_minus_1 = {
        "X-Request-ID": "r1",
        "X-Plugin-Version": "2.0.0",
        "X-Protocol-Version": "1.2",
    }
    headers_n = {
        "X-Request-ID": "r2",
        "X-Plugin-Version": "2.0.0",
        "X-Protocol-Version": "1.3",
    }

    assert validate_protocol_headers(headers_n_minus_1, protocol_range) == (True, None)
    assert validate_protocol_headers(headers_n, protocol_range) == (True, None)


def test_middleware_rejects_out_of_range_with_actionable_message():
    protocol_range = ProtocolRange(min_supported="1.2", max_supported="1.3")

    ok, err = validate_protocol_headers(
        {
            "X-Request-ID": "r3",
            "X-Plugin-Version": "2.0.0",
            "X-Protocol-Version": "1.4",
        },
        protocol_range,
    )

    assert ok is False
    assert err["error"]["code"] == "PROTOCOL_VERSION_UNSUPPORTED"
    assert "Downgrade" in err["error"]["details"]["action"]


def test_bridge_client_runs_handshake_before_text_submit(monkeypatch):
    calls = []

    def fake_urlopen(req):
        calls.append((req.method, req.full_url))
        if req.full_url.endswith("/capabilities"):
            return _FakeResponse(
                {
                    "protocol": {
                        "min_supported": "1.2",
                        "max_supported": "1.3",
                        "recommended": "1.3",
                    },
                    "auth": {"hmacRequired": True},
                }
            )
        if req.full_url.endswith("/jobs/text"):
            body = req.data.decode("utf-8")
            return _FakeResponse({"created": True, "job": {"id": "j1", "echo": json.loads(body)}})
        raise AssertionError(f"Unexpected URL: {req.full_url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = BridgeClient(
        ClientConfig(
            base_url="http://127.0.0.1:7000",
            plugin_version="2.4.1",
            protocol_version="1.3",
        )
    )

    result = client.create_text_job(client_request_id=str(uuid4()), prompt="demo")

    assert calls[0][0] == "GET"
    assert calls[0][1].endswith("/capabilities")
    assert calls[1][0] == "POST"
    assert calls[1][1].endswith("/jobs/text")
    assert result["created"] is True


def test_bridge_client_fails_when_protocol_too_old(monkeypatch):
    def fake_urlopen(req):
        return _FakeResponse(
            {
                "protocol": {
                    "min_supported": "1.2",
                    "max_supported": "1.3",
                    "recommended": "1.3",
                },
                "auth": {"hmacRequired": False},
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = BridgeClient(
        ClientConfig(
            base_url="http://127.0.0.1:7000",
            plugin_version="2.4.1",
            protocol_version="1.1",
        )
    )

    with pytest.raises(RuntimeError, match="upgrade"):
        client.create_text_job(client_request_id=str(uuid4()), prompt="demo")
