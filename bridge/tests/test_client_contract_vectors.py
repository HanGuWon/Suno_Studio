import hashlib
import hmac
import json
from pathlib import Path

from bridge_security import RequestSigner, SignedHeaders


def _sign_reference(secret: str, timestamp: int, nonce: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    payload = f"{timestamp}.{nonce}.{body_hash}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def test_signing_vectors_match_python_request_signer():
    vectors = json.loads(Path("plugin_juce/test_vectors/signing_vectors.json").read_text(encoding="utf-8"))
    signer = RequestSigner(vectors["shared_secret"].encode("utf-8"))

    for case in vectors["cases"]:
        body = case["body"].encode("utf-8")
        headers = signer.sign(body=body, timestamp=case["timestamp"], nonce=case["nonce"])

        expected = _sign_reference(vectors["shared_secret"], case["timestamp"], case["nonce"], body)
        assert headers.signature == expected

        signer.verify(
            SignedHeaders(
                timestamp=case["timestamp"],
                nonce=case["nonce"],
                body_sha256=headers.body_sha256,
                signature=headers.signature,
            ),
            body,
            now=case["timestamp"],
        )


def test_multipart_contract_vectors_present():
    vectors = json.loads(Path("plugin_juce/test_vectors/multipart_vectors.json").read_text(encoding="utf-8"))

    assert vectors["asset_import"]["required_fields"] == ["normalizeOnImport", "file"]
    assert vectors["audio_job"]["required_fields"] == ["clientRequestId", "prompt", "metadata"]
    assert "assetId" in vectors["audio_job"]["optional_fields"]
    assert "file" in vectors["audio_job"]["optional_fields"]


def test_canonical_error_payload_shape_fixture():
    sample = {
        "error": {
            "code": "PROTOCOL_VERSION_UNSUPPORTED",
            "message": "Protocol 9.9 is newer than provider support.",
            "details": {"requested": "9.9"},
            "request_id": "req-123",
        }
    }
    assert set(sample["error"].keys()) == {"code", "message", "details", "request_id"}
