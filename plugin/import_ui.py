"""Plug-in import UI state models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ImportMode(StrEnum):
    IMPORT_ORIGINAL = "import_original"
    IMPORT_NORMALIZED = "import_normalized"


@dataclass(slots=True)
class ImportUiOptions:
    """Import panel configuration shown to users."""

    normalization_available: bool
    selected_mode: ImportMode = ImportMode.IMPORT_ORIGINAL

    def available_modes(self) -> list[ImportMode]:
        modes = [ImportMode.IMPORT_ORIGINAL]
        if self.normalization_available:
            modes.append(ImportMode.IMPORT_NORMALIZED)
        return modes

    def labels(self) -> dict[ImportMode, str]:
        return {
            ImportMode.IMPORT_ORIGINAL: "Import Original",
            ImportMode.IMPORT_NORMALIZED: "Import Normalized",
        }
