import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync('host_adapters/fl_studio/stage_for_playlist.ps1', 'utf8');
const docs = fs.readFileSync('host_adapters/fl_studio/README.md', 'utf8');

assert.match(script, /StageRoot/);
assert.match(script, /Set-Clipboard/);
assert.match(script, /FL64\.exe/);
assert.doesNotMatch(script, /SendKeys|mouse_event|SetCursorPos|\.flp/i);

assert.match(docs, /assisted/i);
assert.match(docs, /does not click FL Studio/i);
assert.match(docs, /does not .*edit `\.flp` files/i);

console.log('FL Studio adapter contract tests passed');
