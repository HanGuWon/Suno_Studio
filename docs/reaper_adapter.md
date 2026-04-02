# REAPER proof-of-concept adapter

## Scripts

- `host_adapters/reaper/insert_generated_file_at_cursor.lua`
  - Inserts chosen generated file at current edit cursor.
- `host_adapters/reaper/export_time_selection_to_file.lua`
  - Prepares export range from time selection (preferred) or selected item (fallback).

## What is automatic vs manual in this phase

Automatic:
- Insert script places selected file at cursor.
- Export script resolves render range.

Manual:
- User chooses output path.
- User executes REAPER render action after range setup.
- Plugin does **not** auto-execute ReaScript yet.

## Handoff model

1. Generate file via plugin/bridge.
2. Either drag file directly into REAPER (generic mode), or run insert script.
3. For audio prompt capture, run export helper script then import output path into bridge.
