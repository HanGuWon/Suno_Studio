from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "fl_studio_smoke_assets"


def _write_u32(value: int) -> bytes:
    return struct.pack(">I", value)


def _write_u16(value: int) -> bytes:
    return struct.pack(">H", value)


def _var_len(value: int) -> bytes:
    parts = [value & 0x7F]
    value >>= 7
    while value:
        parts.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(parts)


def write_wav(path: Path, *, frequency: float) -> None:
    sample_rate = 44_100
    duration_seconds = 1.0
    frame_count = int(sample_rate * duration_seconds)
    amplitude = 0.18
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(frame_count):
            sample = int(math.sin(2 * math.pi * frequency * i / sample_rate) * amplitude * 32767)
            wav.writeframes(struct.pack("<h", sample))


def write_midi(path: Path) -> None:
    ticks_per_quarter = 480
    track = bytearray()
    track += b"\x00\xff\x51\x03\x07\xa1\x20"  # 120 BPM
    track += b"\x00\xc0\x00"  # acoustic grand piano
    track += b"\x00\x90\x3c\x64"  # middle C on
    track += _var_len(ticks_per_quarter)
    track += b"\x80\x3c\x00"  # middle C off
    track += b"\x00\xff\x2f\x00"

    data = bytearray()
    data += b"MThd" + _write_u32(6) + _write_u16(0) + _write_u16(1) + _write_u16(ticks_per_quarter)
    data += b"MTrk" + _write_u32(len(track)) + track
    path.write_bytes(data)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assets = {
        "suno_mix_smoke.wav": lambda p: write_wav(p, frequency=440.0),
        "suno_vocal_stem_smoke.wav": lambda p: write_wav(p, frequency=660.0),
        "suno_tempo_locked_bpm120_smoke.wav": lambda p: write_wav(p, frequency=880.0),
        "suno_midi_smoke.mid": write_midi,
    }
    for name, writer in assets.items():
        writer(OUT / name)
    print(OUT)


if __name__ == "__main__":
    main()
