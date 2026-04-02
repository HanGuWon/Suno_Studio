# User workflows (current phase)

## 1) Text-to-audio (standalone/plugin)
1. Connect to bridge (discovery mode or dev mode).
2. Enter prompt and mode.
3. Submit text job.
4. Poll status until terminal state.
5. Preview output file.
6. Drag output file into DAW/OS (generic workflow).

## 2) Audio-prompt-to-audio
1. Choose local audio file.
2. Client uploads through `/assets/import`.
3. Client submits `/jobs/audio` using returned `assetId`.
4. Poll status and inspect output files.
5. Preview/reveal/drag output.

## 3) REAPER assisted handoff (manual PoC)
1. Generate output in client.
2. Copy/reveal output path from client.
3. Run `insert_generated_file_at_cursor.lua` in REAPER.
4. Select generated file and insert at edit cursor.

## Constraints
- Universal auto-insert across DAWs is not implemented.
- REAPER automation is script-assisted/manual in this phase.
- Real Suno automation is not implemented.
