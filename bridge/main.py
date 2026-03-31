from __future__ import annotations

import os

import uvicorn

from bridge.app import PROTOCOL_RANGE, create_app
from bridge.bootstrap import initialize_runtime_bootstrap


def main() -> None:
    bootstrap = initialize_runtime_bootstrap(protocol_range=PROTOCOL_RANGE)
    app = create_app(
        db_path=os.getenv("BRIDGE_DB_PATH", "storage/jobs.db"),
        assets_root=os.getenv("BRIDGE_ASSETS_ROOT", "storage/assets"),
        enable_hmac=os.getenv("BRIDGE_ENABLE_HMAC", "1") == "1",
        shared_secret=bootstrap.shared_secret,
    )
    uvicorn.run(app, host=bootstrap.host, port=bootstrap.port)


if __name__ == "__main__":
    main()
