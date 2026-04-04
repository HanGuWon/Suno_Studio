# User workflows

## 1) Mock mode (bridge-automated)

1. Connect from plugin or standalone.
2. Set provider to `mock_suno`.
3. Choose mode + requested outputs.
4. Submit text or audio prompt job.
5. Poll updates in UI until complete.
6. Reveal/drag-copy result path.

## 2) Manual Suno mode (human-in-the-loop)

1. Set provider to `manual_suno`.
2. Choose mode + requested outputs + optional sound options.
3. Submit text or audio prompt job.
4. Wait for manual waiting state in UI.
5. Run `Prepare / Fetch Handoff` and open/reveal workspace instructions.
6. Generate and download files manually in Suno UI.
7. Click `Import Suno Results`; client prompts families that were requested and not already imported.
8. Select any subset of families/files and import.
9. Reveal/drag-copy outputs as usual.

## 3) Restart / reconnect behavior

1. Reconnect the client.
2. Client rehydrates last active job from `GET /jobs/{id}`.
3. For manual jobs, client also attempts to recover handoff details.
4. Continue polling, handoff actions, or manual import.

## 4) REAPER assisted path

1. Use reveal or copied path from a completed output.
2. Run REAPER helper scripts.
3. Insert file manually at cursor.

This remains separate from provider generation.
