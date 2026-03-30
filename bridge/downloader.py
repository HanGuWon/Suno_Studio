from __future__ import annotations

import hashlib
from pathlib import Path

from storage.durable_storage import DurableStorage


class AssetDownloader:
    def __init__(self, storage: DurableStorage, root: str | Path = "storage/assets") -> None:
        self.storage = storage
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def store_download(self, *, job_id: str, variant: str, content: bytes, ext: str = "bin") -> tuple[Path, bool]:
        checksum = hashlib.sha256(content).hexdigest()
        filename = f"{job_id}_{variant}_{checksum[:16]}.{ext}"
        out = self.root / filename

        inserted = self.storage.record_downloaded_asset(
            job_id=job_id,
            variant=variant,
            checksum=checksum,
            local_path=str(out),
        )
        if inserted:
            out.write_bytes(content)
        return out, inserted
