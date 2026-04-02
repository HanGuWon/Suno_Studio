from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from bridge.middleware import ProtocolRange
from bridge_security import BridgeBinder, SharedSecretManager


@dataclass(frozen=True)
class RuntimeBootstrap:
    host: str
    port: int
    shared_secret: str
    lockfile: Path | None


def initialize_runtime_bootstrap(*, protocol_range: ProtocolRange) -> RuntimeBootstrap:
    dev_mode = os.getenv("BRIDGE_DEV_MODE", "0") == "1"
    if dev_mode:
        host = os.getenv("BRIDGE_HOST", "127.0.0.1")
        port = int(os.getenv("BRIDGE_PORT", "7071"))
        shared_secret = os.getenv("BRIDGE_SHARED_SECRET", "dev-shared-secret")
        return RuntimeBootstrap(host=host, port=port, shared_secret=shared_secret, lockfile=None)

    lockfile = Path(os.getenv("BRIDGE_LOCKFILE", str(Path.home() / ".suno_studio/bridge.lock")))
    binder = BridgeBinder(lockfile)
    host, port = binder.bind()
    binder.close()

    secret_bytes = SharedSecretManager().get_or_create()
    shared_secret = secret_bytes.hex()
    os.environ["BRIDGE_SHARED_SECRET"] = shared_secret

    discovery = {
        "host": host,
        "port": port,
        "protocol": {
            "min_supported": protocol_range.min_supported,
            "max_supported": protocol_range.max_supported,
        },
        "auth": {
            "hmac": True,
            "shared_secret_bootstrap": "keychain",
        },
    }
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text(json.dumps(discovery, indent=2), encoding="utf-8")
    os.chmod(lockfile, 0o600)
    return RuntimeBootstrap(host=host, port=port, shared_secret=shared_secret, lockfile=lockfile)
