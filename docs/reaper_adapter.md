# REAPER proof-of-concept adapter

The REAPER workflow remains manual-assisted and separate from provider logic.

- You can use outputs from either `mock_suno` jobs or `manual_suno` imported results.
- Client still provides reveal/copy-path handoff.
- REAPER scripts insert/export ranges; they do not automate provider generation.

No universal DAW auto-insert is claimed.
