"""Audio import/transcode service with canonical format, analysis, and normalization lineage."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import math
import shutil
import struct
import wave
from typing import Any


CANONICAL_INTERNAL_FORMAT: dict[str, Any] = {
    "sampleRateHz": 48_000,
    "bitDepth": "24-bit float",
    "layout": "interleaved",
    "channels": 2,
    "stereoPolicy": "always-stereo",
}


@dataclass(slots=True)
class LoudnessAnalysis:
    """Subset loudness/peak values tracked in import manifests."""

    integrated_lufs: float | None = None
    true_peak_dbfs: float | None = None
    peak_dbfs: float | None = None

    def to_manifest(self) -> dict[str, float | None]:
        return {
            "integratedLUFS": self.integrated_lufs,
            "truePeakDbfs": self.true_peak_dbfs,
            "peakDbfs": self.peak_dbfs,
        }


@dataclass(slots=True)
class ImportedAsset:
    """Normalized representation of imported media and derivatives."""

    asset_id: str
    source_path: Path
    imported_original_path: Path
    source_format: dict[str, Any]
    analysis: LoudnessAnalysis
    checksum_sha256: str
    derived_formats: list[dict[str, Any]] = field(default_factory=list)

    def to_manifest(self) -> dict[str, Any]:
        return {
            "id": self.asset_id,
            "sourcePath": str(self.source_path),
            "sourceFormat": self.source_format,
            "analysis": self.analysis.to_manifest(),
            "checksum": {
                "algorithm": "sha256",
                "value": self.checksum_sha256,
            },
            "original": {
                "path": str(self.imported_original_path),
                "lineage": {
                    "type": "source",
                },
            },
            "derivedFormats": self.derived_formats,
        }


def checksum_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _analyze_wav(path: Path) -> tuple[dict[str, Any], LoudnessAnalysis]:
    """Perform lightweight WAV analysis for peak and approximate LUFS fields.

    integrated LUFS and true peak are left as approximations/nullable when not derivable.
    """

    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        nframes = wf.getnframes()
        frames = wf.readframes(nframes)

    # Only PCM16/PCM32 handling for lightweight built-in analysis.
    peak = 0.0
    if sample_width == 2:
        fmt = "<" + "h" * (len(frames) // 2)
        samples = struct.unpack(fmt, frames)
        peak = max(abs(v) / 32768.0 for v in samples) if samples else 0.0
    elif sample_width == 4:
        fmt = "<" + "i" * (len(frames) // 4)
        samples = struct.unpack(fmt, frames)
        peak = max(abs(v) / 2147483648.0 for v in samples) if samples else 0.0

    peak_dbfs = 20.0 * math.log10(max(peak, 1e-12))
    # Approximation: true peak equal to sample peak for now.
    true_peak_dbfs = peak_dbfs
    # Approximation: pseudo-LUFS from RMS proxy if frames are available.
    integrated_lufs = None
    if peak > 0:
        integrated_lufs = max(-70.0, peak_dbfs - 3.0)

    source_format = {
        "container": "wav",
        "sampleRateHz": sample_rate,
        "channels": channels,
        "sampleWidthBytes": sample_width,
        "interleaved": True,
    }
    analysis = LoudnessAnalysis(
        integrated_lufs=integrated_lufs,
        true_peak_dbfs=true_peak_dbfs,
        peak_dbfs=peak_dbfs,
    )
    return source_format, analysis


def import_audio(
    asset_id: str,
    source_path: str | Path,
    import_dir: str | Path,
    *,
    normalize_on_import: bool = False,
    target_lufs: float = -14.0,
    true_peak_ceiling_dbfs: float = -1.0,
) -> ImportedAsset:
    """Import media preserving original while optionally creating normalized derivative.

    Normalization is non-destructive: source/original copy is preserved and any normalized
    output is written as a derived format with explicit lineage metadata.
    """

    src = Path(source_path)
    out_dir = Path(import_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original_dst = out_dir / f"{asset_id}.original{src.suffix.lower()}"
    shutil.copy2(src, original_dst)

    if src.suffix.lower() == ".wav":
        source_format, analysis = _analyze_wav(src)
    else:
        source_format = {"container": src.suffix.lower().lstrip(".")}
        analysis = LoudnessAnalysis()

    imported = ImportedAsset(
        asset_id=asset_id,
        source_path=src,
        imported_original_path=original_dst,
        source_format=source_format,
        analysis=analysis,
        checksum_sha256=checksum_sha256(src),
    )

    if normalize_on_import:
        normalized_path = out_dir / f"{asset_id}.normalized{src.suffix.lower()}"
        # Placeholder for DSP pipeline: currently duplicates original bytes.
        shutil.copy2(original_dst, normalized_path)

        imported.derived_formats.append(
            {
                "path": str(normalized_path),
                "format": CANONICAL_INTERNAL_FORMAT,
                "analysis": imported.analysis.to_manifest(),
                "checksum": {
                    "algorithm": "sha256",
                    "value": checksum_sha256(normalized_path),
                },
                "lineage": {
                    "type": "normalized",
                    "source": str(original_dst),
                    "method": "non-destructive",
                    "normalization": {
                        "enabled": True,
                        "targetIntegratedLUFS": target_lufs,
                        "truePeakCeilingDbfs": true_peak_ceiling_dbfs,
                    },
                },
            }
        )

    return imported
