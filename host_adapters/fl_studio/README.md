# FL Studio assisted adapter

FL Studio does not expose the same simple external scripting surface as the
REAPER helper scripts in this repository. The supported beta path is therefore
assisted, not a silent Playlist insert:

1. Stage completed Suno Studio output files into the FL Studio user data tree.
2. Copy the staged file path(s) to the clipboard.
3. Optionally launch FL Studio.
4. Drop or paste the staged file into the Playlist or Sampler.

## Usage

```powershell
powershell -ExecutionPolicy Bypass -File host_adapters/fl_studio/stage_for_playlist.ps1 `
  -Path "C:\path\to\result.wav" `
  -LaunchFL
```

By default, files are copied to:

```text
%USERPROFILE%\Documents\Image-Line\FL Studio\Audio\Suno Studio
```

Use `-StageRoot` to test or override the staging folder, and `-FLStudioExe` if
FL Studio is installed outside the common Image-Line paths.

## Boundary

This adapter does not click FL Studio, edit `.flp` files, or claim current
Playlist cursor insertion. It prepares files in a stable FL Studio-visible
location and hands the final placement to the user.
