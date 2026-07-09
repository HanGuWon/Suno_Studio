# FL Studio adapter path

## Current practical integration

The reliable path for FL Studio is assisted file staging:

- the JUCE client can drag/copy completed output paths
- the Downloads watcher can collect Suno-downloaded files
- `host_adapters/fl_studio/stage_for_playlist.ps1` can copy completed output into
  the FL Studio user data tree and copy staged paths to the clipboard

On this machine, FL Studio 2025 was detected at:

```text
C:\Program Files\Image-Line\FL Studio 2025\FL64.exe
```

The default staging folder is:

```text
%USERPROFILE%\Documents\Image-Line\FL Studio\Audio\Suno Studio
```

## Smoke command

```powershell
python tools/make_fl_studio_smoke_assets.py
powershell -ExecutionPolicy Bypass -File host_adapters/fl_studio/stage_for_playlist.ps1 `
  -Path build/fl_studio_smoke_assets/suno_mix_smoke.wav `
  -StageRoot build/fl_studio_stage_test
```

The script returns JSON containing staged file paths. It also copies those paths
to the clipboard for manual drop/paste into FL Studio.

## Why not direct Playlist insertion yet

Direct Playlist insertion would require one of:

- a documented FL Studio command-line media import contract
- a supported remote-control/API surface for Playlist placement
- UI automation that clicks the user interface

This repository keeps the beta path deterministic and user-controlled, so it
does not edit `.flp` internals or drive the FL Studio UI by coordinates.
