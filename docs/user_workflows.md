# User workflows (current phase)

## 1) Text to audio (generic host)
1. Open plugin.
2. Enter prompt and mode.
3. Submit job.
4. Poll status in job list.
5. Preview generated file.
6. Drag generated WAV from plugin to DAW timeline.

## 2) Audio prompt to audio
1. Drop local audio file in plugin or choose file.
2. Plugin imports file into bridge (`/assets/import`).
3. Plugin submits `/jobs/audio` with returned `assetId`.
4. Poll status, preview result, drag into DAW.

## 3) REAPER assisted insertion
1. Generate output.
2. Run `insert_generated_file_at_cursor.lua`.
3. Choose generated file.
4. Script inserts media at edit cursor.

## Important constraints
- Universal auto-insert across all DAWs is **not implemented**.
- REAPER automation is proof-of-concept only.
