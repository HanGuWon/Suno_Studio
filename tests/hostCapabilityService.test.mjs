import assert from 'node:assert/strict';
import { HostCapabilityService, MemoryOverrideStore, MODE } from '../src/services/HostCapabilityService.js';
import { buildCapabilityPanelModel, applyFallbackAction } from '../src/ui/hostCapabilityPanel.js';

const store = new MemoryOverrideStore();
const service = new HostCapabilityService({ overrideStore: store });

const auto = service.resolveMode({ host: 'logic-pro', version: '11.0.1', format: 'wav' });
assert.equal(auto.mode, MODE.AUTO_INSERT);
assert.equal(auto.statusBadge, 'Auto Insert');
assert.equal(auto.fallbackAction.targetMode, MODE.DRAG_TO_TIMELINE);

const drag = service.resolveMode({ host: 'pro-tools', version: '2024.10', format: 'wav' });
assert.equal(drag.mode, MODE.DRAG_TO_TIMELINE);
assert.equal(drag.statusBadge, 'Drag to Timeline');

const unknown = service.resolveMode({ host: 'unknown-host', version: '1', format: 'wav' });
assert.equal(unknown.mode, MODE.MANUAL_IMPORT);
assert.equal(unknown.statusBadge, 'Manual Import');

const panel = buildCapabilityPanelModel(auto);
assert.equal(panel.badge, 'Auto Insert');

applyFallbackAction(service, 'logic-pro', auto.fallbackAction);
const overridden = service.resolveMode({ host: 'logic-pro', version: '11.0.1', format: 'wav' });
assert.equal(overridden.mode, MODE.DRAG_TO_TIMELINE);
assert.equal(overridden.source, 'override');

console.log('hostCapabilityService tests passed');
