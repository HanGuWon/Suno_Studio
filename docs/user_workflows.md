# User workflows

## 1) Mock mode (fully automated bridge loop)
1. Connect client to bridge.
2. Submit text/audio with `providerMode=mock_suno`.
3. Poll until terminal.
4. Preview/reveal/drag output.

## 2) Manual Suno mode (human-in-the-loop)
1. Submit text/audio with `providerMode=manual_suno`.
2. Wait for `awaiting_manual_provider_result`.
3. Open handoff package/instructions from workspace.
4. Perform generation manually in Suno UI.
5. Import downloaded files with manual completion endpoint.
6. Preview/reveal/drag imported outputs.

## 3) REAPER assisted path
1. Use client reveal/copy path from generated/imported output.
2. Run REAPER helper scripts.
3. Insert file manually at cursor.
