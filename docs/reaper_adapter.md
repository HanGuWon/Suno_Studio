# REAPER proof-of-concept adapter

## Scripts

- `host_adapters/reaper/insert_generated_file_at_cursor.lua`
  - inserts selected generated file at current edit cursor.
- `host_adapters/reaper/export_time_selection_to_file.lua`
  - prepares export range from time selection (preferred) or selected item.

## Client handoff in this phase

- From plugin/standalone client:
  - reveal selected output file, or
  - copy selected output path.

- In REAPER:
  - run insert script and choose generated file.

## Automatic vs manual

Automatic:
- REAPER script actions themselves.

Manual:
- user selects file/path
- user runs script
- plugin does not auto-run ReaScript yet

This is intentionally a manual-assisted PoC, not universal DAW automation.
