from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from bridge.adapters.base import ProviderAdapter, ProviderOutput, ProviderPollResult


class ManualSunoAdapter(ProviderAdapter):
    """Compliance-first adapter that prepares handoff artifacts for manual Suno usage.

    This adapter intentionally does not perform network automation, scraping, or polling.
    """

    def __init__(self, workspaces_root: Path) -> None:
        self.workspaces_root = Path(workspaces_root)
        self.workspaces_root.mkdir(parents=True, exist_ok=True)

    def submit_text_job(self, *, job_id: str, prompt: str, metadata: dict) -> str:
        self._write_workspace(job_id=job_id, prompt=prompt, metadata=metadata, source_path=None)
        return f"manual-{job_id}"

    def submit_audio_job(self, *, job_id: str, prompt: str, metadata: dict, source_path: Path) -> str:
        self._write_workspace(job_id=job_id, prompt=prompt, metadata=metadata, source_path=source_path)
        return f"manual-{job_id}"

    def poll_job(self, remote_job_id: str) -> ProviderPollResult:
        return ProviderPollResult(state="awaiting_manual_result", progress=0.5)

    def download_outputs(self, remote_job_id: str) -> list[ProviderOutput]:
        return []

    def cancel_remote_job(self, remote_job_id: str) -> bool:
        return True

    def get_handoff(self, job_id: str) -> dict[str, Any]:
        workspace = self.workspace_for_job(job_id)
        handoff_path = workspace / "handoff.json"
        if not handoff_path.exists():
            raise FileNotFoundError(f"handoff not prepared for {job_id}")
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        return {
            "workspace": str(workspace),
            "handoff": handoff,
            "instructionsPath": str(workspace / "README.md"),
        }

    def workspace_for_job(self, job_id: str) -> Path:
        return self.workspaces_root / job_id

    def _write_workspace(self, *, job_id: str, prompt: str, metadata: dict[str, Any], source_path: Path | None) -> None:
        workspace = self.workspace_for_job(job_id)
        workspace.mkdir(parents=True, exist_ok=True)
        requested = {
            "mix": bool(metadata.get("request_mix", True)),
            "stems": bool(metadata.get("request_stems", False)),
            "tempo_locked_stems": bool(metadata.get("request_tempo_locked_stems", False)),
            "midi": bool(metadata.get("request_midi", False)),
            "selected_range_export": bool(metadata.get("request_selected_range_export", False)),
        }
        handoff = {
            "provider": "suno_manual",
            "job_id": job_id,
            "mode": metadata.get("mode", "song"),
            "prompt": prompt,
            "audio_prompt_asset_id": metadata.get("audio_prompt_asset_id"),
            "sound_options": {
                "one_shot": metadata.get("one_shot"),
                "loop": metadata.get("loop"),
                "bpm": metadata.get("bpm"),
                "key": metadata.get("key"),
            },
            "requested_deliverables": requested,
        }
        (workspace / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        (workspace / "prompt.txt").write_text(prompt or "", encoding="utf-8")
        (workspace / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        source_dir = workspace / "source_audio"
        source_dir.mkdir(exist_ok=True)
        if source_path and source_path.exists():
            shutil.copy2(source_path, source_dir / source_path.name)

        instructions = """# Manual Suno Handoff Steps

1. Open Suno using your normal account and UI.
2. Use `prompt.txt`, optional `source_audio/`, and `handoff.json` as your job guide.
3. Request only deliverables listed under `requested_deliverables`.
4. Download results locally from Suno.
5. Return to client and use Import Suno Results for this job.

Notes:
- No browser automation or unofficial API is used by this project.
- Requested deliverables may differ from files you actually receive.
"""
        (workspace / "README.md").write_text(instructions, encoding="utf-8")
