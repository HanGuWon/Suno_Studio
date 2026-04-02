import assert from 'node:assert/strict';
import fs from 'node:fs';

const insertScript = fs.readFileSync('host_adapters/reaper/insert_generated_file_at_cursor.lua', 'utf8');
const exportScript = fs.readFileSync('host_adapters/reaper/export_time_selection_to_file.lua', 'utf8');

assert.ok(insertScript.includes('reaper.GetCursorPosition'));
assert.ok(insertScript.includes('reaper.InsertMedia'));
assert.ok(insertScript.includes('generated_file_path'));

assert.ok(exportScript.includes('GetSet_LoopTimeRange'));
assert.ok(exportScript.includes('GetSelectedMediaItem'));
assert.ok(exportScript.includes('Render range prepared'));

console.log('reaper adapter contract tests passed');
