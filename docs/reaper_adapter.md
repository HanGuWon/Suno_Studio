# REAPER proof-of-concept adapter

REAPER integration remains manual-assisted and intentionally separate from provider workflows.

- Works with outputs from both `mock_suno` and `manual_suno` imported results.
- JUCE client provides reveal/copy/drag handoff only.
- REAPER scripts assist export/import at cursor.

Not in scope here:

- universal DAW auto-insert
- automatic timeline placement across hosts
- provider automation inside REAPER
