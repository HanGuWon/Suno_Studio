"""Security baseline primitives for local plugin<->bridge communication.

This module implements:
- Per-install shared secret bootstrap backed by OS credential stores.
- HMAC-signed request verification with timestamp/nonce/body integrity.
- Replay protection.
- Loopback-only random high-port binding with lockfile discovery.
- Log redaction with opt-in secure debug mode.
- Encrypted-at-rest session artifact storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


SERVICE_NAME = "suno_studio_bridge"
ACCOUNT_NAME = "install_shared_secret"
DEFAULT_SKEW_SECONDS = 120
NONCE_TTL_SECONDS = 300


class CredentialStoreError(RuntimeError):
    """Raised when the OS credential store is unavailable."""


class ReplayDetectedError(RuntimeError):
    """Raised when a signed request reuses a known nonce."""


class SignatureValidationError(RuntimeError):
    """Raised when signature validation fails."""


class ExpiredRequestError(RuntimeError):
    """Raised when a request timestamp is outside allowed skew."""


class OSKeychain:
    """Cross-platform best-effort wrapper over native credential stores."""

    def __init__(self, service: str = SERVICE_NAME, account: str = ACCOUNT_NAME) -> None:
        self.service = service
        self.account = account

    def get(self) -> Optional[str]:
        if os.name == "nt":
            return self._win_get()
        if os.uname().sysname == "Darwin":
            return self._mac_get()
        return self._linux_get()

    def set(self, value: str) -> None:
        if os.name == "nt":
            self._win_set(value)
            return
        if os.uname().sysname == "Darwin":
            self._mac_set(value)
            return
        self._linux_set(value)

    def _mac_get(self) -> Optional[str]:
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                self.service,
                "-a",
                self.account,
                "-w",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None

    def _mac_set(self, value: str) -> None:
        proc = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                self.service,
                "-a",
                self.account,
                "-w",
                value,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CredentialStoreError(proc.stderr.strip() or "failed to store credential")

    def _linux_get(self) -> Optional[str]:
        proc = subprocess.run(
            ["secret-tool", "lookup", "service", self.service, "account", self.account],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None

    def _linux_set(self, value: str) -> None:
        proc = subprocess.run(
            [
                "secret-tool",
                "store",
                "--label",
                f"{self.service}:{self.account}",
                "service",
                self.service,
                "account",
                self.account,
            ],
            input=value,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CredentialStoreError(proc.stderr.strip() or "failed to store credential")

    def _win_get(self) -> Optional[str]:
        target = f"{self.service}:{self.account}"
        proc = subprocess.run(["cmdkey", "/list"], capture_output=True, text=True)
        if proc.returncode != 0 or target not in proc.stdout:
            return None
        blob_path = Path.home() / ".suno_studio" / "windows_cred_fallback.json"
        if not blob_path.exists():
            return None
        data = json.loads(blob_path.read_text())
        return data.get(target)

    def _win_set(self, value: str) -> None:
        target = f"{self.service}:{self.account}"
        proc = subprocess.run(
            ["cmdkey", f"/generic:{target}", "/user:suno", "/pass:managed"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CredentialStoreError(proc.stderr.strip() or "failed to register Windows credential")
        blob_path = Path.home() / ".suno_studio" / "windows_cred_fallback.json"
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, str] = {}
        if blob_path.exists():
            data = json.loads(blob_path.read_text())
        data[target] = value
        blob_path.write_text(json.dumps(data))
        os.chmod(blob_path, 0o600)


class SharedSecretManager:
    """Generates and loads one per-install shared secret."""

    def __init__(self, keychain: Optional[OSKeychain] = None) -> None:
        self.keychain = keychain or OSKeychain()

    def get_or_create(self) -> bytes:
        existing = self.keychain.get()
        if existing:
            return base64.urlsafe_b64decode(existing.encode("utf-8"))
        raw = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(raw).decode("utf-8")
        self.keychain.set(encoded)
        return raw


class NonceCache:
    """In-memory nonce replay cache."""

    def __init__(self, ttl_seconds: int = NONCE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._seen: Dict[str, float] = {}

    def add(self, nonce: str, now: Optional[float] = None) -> None:
        now = now or time.time()
        self._prune(now)
        if nonce in self._seen:
            raise ReplayDetectedError("nonce has already been used")
        self._seen[nonce] = now + self.ttl_seconds

    def _prune(self, now: float) -> None:
        expired = [n for n, expiry in self._seen.items() if expiry < now]
        for nonce in expired:
            del self._seen[nonce]


@dataclass
class SignedHeaders:
    timestamp: int
    nonce: str
    body_sha256: str
    signature: str


class RequestSigner:
    """Signs and verifies plugin->bridge requests."""

    def __init__(self, shared_secret: bytes, skew_seconds: int = DEFAULT_SKEW_SECONDS) -> None:
        self.shared_secret = shared_secret
        self.skew_seconds = skew_seconds
        self.nonce_cache = NonceCache()

    def sign(self, body: bytes, timestamp: Optional[int] = None, nonce: Optional[str] = None) -> SignedHeaders:
        ts = timestamp or int(time.time())
        nonce_value = nonce or secrets.token_urlsafe(24)
        body_hash = hashlib.sha256(body).hexdigest()
        payload = f"{ts}.{nonce_value}.{body_hash}".encode("utf-8")
        sig = hmac.new(self.shared_secret, payload, hashlib.sha256).hexdigest()
        return SignedHeaders(timestamp=ts, nonce=nonce_value, body_sha256=body_hash, signature=sig)

    def verify(self, headers: SignedHeaders, body: bytes, now: Optional[int] = None) -> None:
        current = now or int(time.time())
        if abs(current - headers.timestamp) > self.skew_seconds:
            raise ExpiredRequestError("request timestamp outside allowed skew")

        observed_hash = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(observed_hash, headers.body_sha256):
            raise SignatureValidationError("body hash mismatch")

        payload = f"{headers.timestamp}.{headers.nonce}.{headers.body_sha256}".encode("utf-8")
        expected = hmac.new(self.shared_secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, headers.signature):
            raise SignatureValidationError("invalid request signature")

        self.nonce_cache.add(headers.nonce, now=float(current))


class BridgeBinder:
    """Bind to loopback on random high port and emit lockfile discovery."""

    def __init__(self, lockfile: Path) -> None:
        self.lockfile = lockfile
        self.sock: Optional[socket.socket] = None

    def bind(self) -> Tuple[str, int]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(("127.0.0.1", 0))
        sock.listen(64)

        host, port = sock.getsockname()
        token = secrets.token_urlsafe(32)
        self.lockfile.parent.mkdir(parents=True, exist_ok=True)
        self.lockfile.write_text(
            json.dumps({"host": host, "port": port, "discovery_token": token, "pid": os.getpid()}),
            encoding="utf-8",
        )
        os.chmod(self.lockfile, 0o600)
        self.sock = sock
        return host, port

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        if self.lockfile.exists():
            self.lockfile.unlink()


REDACT_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "token",
    "access_token",
    "refresh_token",
    "prompt",
    "session",
}


class RedactingFormatter(logging.Formatter):
    """Redacts sensitive fields from structured logs."""

    def __init__(self, secure_debug: bool = False) -> None:
        super().__init__("%(asctime)s %(levelname)s %(message)s")
        self.secure_debug = secure_debug

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.secure_debug:
            return super().format(record)
        return f"{record.levelname} {self._redact_text(message)}"

    def _redact_text(self, text: str) -> str:
        lowered = text.lower()
        if not any(k in lowered for k in REDACT_KEYS):
            return text
        redacted = text
        for key in REDACT_KEYS:
            redacted = redacted.replace(key, f"{key[:2]}***")
        return redacted


def build_secure_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    secure_debug = os.getenv("BRIDGE_SECURE_DEBUG", "0") == "1"
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter(secure_debug=secure_debug))
    logger.handlers = [handler]
    logger.propagate = False
    return logger


class SessionCrypto:
    """Encrypt/decrypt persisted provider sessions at rest."""

    def __init__(self, shared_secret: bytes) -> None:
        self._enc_key = hashlib.pbkdf2_hmac("sha256", shared_secret, b"session-enc", 100_000, dklen=32)
        self._mac_key = hashlib.pbkdf2_hmac("sha256", shared_secret, b"session-mac", 100_000, dklen=32)

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(16)
        keystream = self._keystream(nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream))
        mac = hmac.new(self._mac_key, nonce + ciphertext, hashlib.sha256).digest()
        return nonce + mac + ciphertext

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < 48:
            raise ValueError("ciphertext too short")
        nonce, mac, ciphertext = blob[:16], blob[16:48], blob[48:]
        expected = hmac.new(self._mac_key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError("ciphertext integrity failure")
        keystream = self._keystream(nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, keystream))

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        blocks = []
        counter = 0
        while sum(len(b) for b in blocks) < length:
            block = hashlib.sha256(self._enc_key + nonce + counter.to_bytes(8, "big")).digest()
            blocks.append(block)
            counter += 1
        return b"".join(blocks)[:length]


class EncryptedSessionStore:
    """Filesystem-backed encrypted session artifact storage."""

    def __init__(self, root: Path, crypto: SessionCrypto) -> None:
        self.root = root
        self.crypto = crypto
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def write(self, name: str, payload: bytes) -> Path:
        target = self.root / f"{name}.bin"
        encrypted = self.crypto.encrypt(payload)
        target.write_bytes(encrypted)
        os.chmod(target, 0o600)
        return target

    def read(self, name: str) -> bytes:
        target = self.root / f"{name}.bin"
        return self.crypto.decrypt(target.read_bytes())
