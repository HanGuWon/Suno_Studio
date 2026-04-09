# User workflows

## 1) Mock mode (bridge-automated)

1. Connect from plugin or standalone.
2. Set provider to `mock_suno`.
3. Choose mode + requested outputs.
4. Submit text or audio prompt job.
5. Poll updates in UI until complete.
6. Reveal/drag-copy result path (preview is currently disabled).

## 2) Manual Suno mode (human-in-the-loop)

1. Set provider to `manual_suno`.
2. Choose mode + requested outputs + optional sound options.
3. Submit text or audio prompt job.
4. Wait for manual waiting state in UI.
5. Run `Prepare / Fetch Handoff` and open/reveal workspace instructions.
6. Generate and download files manually in Suno UI.
7. Click `Import Suno Results`; the picker prompts only for requested + not-yet-imported families.
8. You can cancel any family picker; the client skips `/manual-complete` unless at least one file was selected.
9. Client calls `/jobs/{job_id}/manual-complete`, then reveal/drag as usual.

## 3) REAPER assisted path

1. Use reveal or copied path from a completed output.
2. Run REAPER helper scripts.
3. Insert file manually at cursor.

This remains separate from provider generation.
