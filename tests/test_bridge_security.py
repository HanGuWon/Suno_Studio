import time
from pathlib import Path

from bridge_security import (
    BridgeBinder,
    EncryptedSessionStore,
    ExpiredRequestError,
    ReplayDetectedError,
    RequestSigner,
    SessionCrypto,
)


def test_sign_and_verify_roundtrip():
    signer = RequestSigner(b"a" * 32)
    body = b'{"hello":"world"}'
    headers = signer.sign(body=body, timestamp=int(time.time()), nonce="abc123")
    signer.verify(headers, body)


def test_replay_is_rejected():
    signer = RequestSigner(b"b" * 32)
    body = b"x"
    now = int(time.time())
    headers = signer.sign(body=body, timestamp=now, nonce="nonce1")
    signer.verify(headers, body, now=now)
    try:
        signer.verify(headers, body, now=now)
        assert False, "expected replay rejection"
    except ReplayDetectedError:
        pass


def test_expired_is_rejected():
    signer = RequestSigner(b"c" * 32, skew_seconds=1)
    body = b"x"
    headers = signer.sign(body=body, timestamp=1, nonce="old")
    try:
        signer.verify(headers, body, now=10)
        assert False, "expected expiry"
    except ExpiredRequestError:
        pass


def test_session_store_encrypts(tmp_path: Path):
    crypto = SessionCrypto(b"d" * 32)
    store = EncryptedSessionStore(tmp_path / "sessions", crypto)
    payload = b"super-secret-session"
    path = store.write("provider", payload)
    assert path.read_bytes() != payload
    assert store.read("provider") == payload


def test_bridge_binds_loopback_and_writes_lockfile(tmp_path: Path):
    binder = BridgeBinder(tmp_path / "bridge.lock")
    host, port = binder.bind()
    try:
        assert host == "127.0.0.1"
        assert port > 0
        assert (tmp_path / "bridge.lock").exists()
    finally:
        binder.close()
