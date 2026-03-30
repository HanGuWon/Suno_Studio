import { MODE } from '../services/HostCapabilityService.js';

/**
 * Produces UI-ready state with explicit badge and one-click fallback action.
 */
export function buildCapabilityPanelModel(resolution) {
  return {
    badge: resolution.statusBadge,
    detailRows: [
      { label: 'Mode source', value: resolution.source },
      { label: 'Host', value: resolution.host },
      { label: 'Version', value: resolution.version },
      { label: 'Format', value: resolution.format },
    ],
    fallbackAction: resolution.fallbackAction,
  };
}

/**
 * Small helper that can be wired to UI buttons.
 */
export function applyFallbackAction(service, host, action) {
  if (!action || !action.targetMode) {
    return null;
  }

  const reason =
    action.targetMode === MODE.DRAG_TO_TIMELINE
      ? 'fallback from auto insert'
      : action.targetMode === MODE.MANUAL_IMPORT
        ? 'fallback to manual import'
        : 'fallback action';

  service.setHostOverride(host, action.targetMode, reason);
  return action.targetMode;
}
