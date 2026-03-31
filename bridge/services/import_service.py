from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from bridge.schemas.manifest_schema import MANIFEST_SCHEMA
from bridge.services.transcode_service import import_audio
from storage.durable_storage import DurableStorage


class ManifestValidationError(ValueError):
    pass


class ImportService:
    def __init__(self, storage: DurableStorage, assets_root: str | Path = "storage/assets/imported") -> None:
        self.storage = storage
        self.assets_root = Path(assets_root)
        self.assets_root.mkdir(parents=True, exist_ok=True)

    def import_file(self, source_path: Path, *, normalize_on_import: bool = False) -> dict:
        asset_id = str(uuid4())
        import_dir = self.assets_root / asset_id
        imported = import_audio(
            asset_id=asset_id,
            source_path=source_path,
            import_dir=import_dir,
            normalize_on_import=normalize_on_import,
        )
        manifest = imported.to_manifest()
        self._validate_manifest(manifest)

        manifest_path = import_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.storage.save_imported_asset(asset_id, manifest)
        return manifest

    def _validate_manifest(self, manifest: dict) -> None:
        required = set(MANIFEST_SCHEMA["required"])
        missing = [key for key in required if key not in manifest]
        if missing:
            raise ManifestValidationError(f"manifest missing required keys: {missing}")

        checksum = manifest["checksum"]["value"]
        if len(checksum) != 64:
            raise ManifestValidationError("manifest checksum must be 64-char sha256")
