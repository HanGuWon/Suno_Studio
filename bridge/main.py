from __future__ import annotations

import os

import uvicorn

from bridge.app import create_app


def main() -> None:
    host = os.getenv("BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("BRIDGE_PORT", "7071"))
    app = create_app(
        db_path=os.getenv("BRIDGE_DB_PATH", "storage/jobs.db"),
        assets_root=os.getenv("BRIDGE_ASSETS_ROOT", "storage/assets"),
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
