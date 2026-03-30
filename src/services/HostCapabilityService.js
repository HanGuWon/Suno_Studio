/**
 * HostCapabilityService resolves capability mode for host/version/format tuples.
 * Resolution is deterministic: override > profile exact match > profile fallback > manual import.
 */

const DEFAULT_PROFILE_VERSION = '2026.03';

const BUILTIN_PROFILES = {
  '2026.03': {
    hosts: {
      'logic-pro': {
        versions: ['11'],
        formats: {
          wav: {
            transportFields: ['tempoMap', 'cycleRange', 'smpteStart'],
            editCursorAccess: true,
            selectionExport: true,
            autoMediaInsertion: true,
            araAvailable: false,
            dragDropReliabilityNotes:
              'Strong timeline drop support; frozen tracks may ignore first drop.',
          },
          aiff: {
            transportFields: ['tempoMap', 'cycleRange', 'smpteStart'],
            editCursorAccess: true,
            selectionExport: true,
            autoMediaInsertion: true,
            araAvailable: false,
            dragDropReliabilityNotes:
              'AIFF drag/drop mirrors WAV behavior in track lanes.',
          },
        },
      },
      'cubase-pro': {
        versions: ['13'],
        formats: {
          wav: {
            transportFields: ['tempoTrack', 'rulerFormat', 'frameRate'],
            editCursorAccess: true,
            selectionExport: true,
            autoMediaInsertion: true,
            araAvailable: true,
            dragDropReliabilityNotes:
              'Stable in project window; insertion timing can drift with constrained compensation.',
          },
        },
      },
      'ableton-live': {
        versions: ['12'],
        formats: {
          wav: {
            transportFields: ['tempo', 'globalQuantization', 'songTime'],
            editCursorAccess: false,
            selectionExport: false,
            autoMediaInsertion: false,
            araAvailable: false,
            dragDropReliabilityNotes:
              'Session view drag is robust; arrangement drops can shift when warp is active.',
          },
        },
      },
      'pro-tools': {
        versions: ['2024'],
        formats: {
          wav: {
            transportFields: ['tempo', 'timeSignature', 'barsBeats', 'sampleRate'],
            editCursorAccess: false,
            selectionExport: false,
            autoMediaInsertion: false,
            araAvailable: false,
            dragDropReliabilityNotes:
              'Clip drag is reliable; marker lanes can intermittently reject drops.',
          },
        },
      },
    },
  },
};

const MODE = {
  AUTO_INSERT: 'AUTO_INSERT',
  DRAG_TO_TIMELINE: 'DRAG_TO_TIMELINE',
  MANUAL_IMPORT: 'MANUAL_IMPORT',
};

class MemoryOverrideStore {
  constructor() {
    this.map = new Map();
  }

  getItem(key) {
    return this.map.has(key) ? this.map.get(key) : null;
  }

  setItem(key, value) {
    this.map.set(key, value);
  }
}

function defaultStore() {
  if (typeof globalThis !== 'undefined' && globalThis.localStorage) {
    return globalThis.localStorage;
  }
  return new MemoryOverrideStore();
}

function normalizeHost(host) {
  return String(host || '').trim().toLowerCase();
}

function normalizeVersion(version) {
  return String(version || '').trim();
}

function normalizeFormat(format) {
  return String(format || '').trim().toLowerCase();
}

function hostOverrideKey(host) {
  return `host-capability-override:${host}`;
}

function startsWithAny(candidate, prefixes) {
  return prefixes.some((prefix) => candidate.startsWith(prefix));
}

export class HostCapabilityService {
  constructor({ profiles = BUILTIN_PROFILES, profileVersion = DEFAULT_PROFILE_VERSION, overrideStore } = {}) {
    this.profiles = profiles;
    this.profileVersion = profileVersion;
    this.overrideStore = overrideStore || defaultStore();
  }

  loadProfile(version = this.profileVersion) {
    const profile = this.profiles[version];
    if (!profile) {
      throw new Error(`Capability profile not found for version: ${version}`);
    }

    this.profileVersion = version;
    return profile;
  }

  getHostOverride(host) {
    const normalizedHost = normalizeHost(host);
    const raw = this.overrideStore.getItem(hostOverrideKey(normalizedHost));
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw);
      if (!Object.values(MODE).includes(parsed.mode)) {
        return null;
      }
      return parsed;
    } catch (_error) {
      return null;
    }
  }

  setHostOverride(host, mode, reason = 'manual override') {
    const normalizedHost = normalizeHost(host);
    const payload = JSON.stringify({
      mode,
      reason,
      updatedAt: new Date().toISOString(),
    });
    this.overrideStore.setItem(hostOverrideKey(normalizedHost), payload);
  }

  resolveMode({ host, version, format }) {
    const normalizedHost = normalizeHost(host);
    const normalizedVersion = normalizeVersion(version);
    const normalizedFormat = normalizeFormat(format);

    const override = this.getHostOverride(normalizedHost);
    if (override) {
      return this.#decorateResolution({
        mode: override.mode,
        source: 'override',
        capability: null,
        host: normalizedHost,
        version: normalizedVersion,
        format: normalizedFormat,
      });
    }

    const profile = this.loadProfile();
    const hostProfile = profile.hosts[normalizedHost];
    if (!hostProfile) {
      return this.#decorateResolution({
        mode: MODE.MANUAL_IMPORT,
        source: 'unknown-host',
        capability: null,
        host: normalizedHost,
        version: normalizedVersion,
        format: normalizedFormat,
      });
    }

    const versionSupported = startsWithAny(normalizedVersion, hostProfile.versions);
    const capability = hostProfile.formats[normalizedFormat] || null;

    if (!versionSupported || !capability) {
      return this.#decorateResolution({
        mode: MODE.MANUAL_IMPORT,
        source: 'unsupported-combination',
        capability,
        host: normalizedHost,
        version: normalizedVersion,
        format: normalizedFormat,
      });
    }

    if (capability.autoMediaInsertion) {
      return this.#decorateResolution({
        mode: MODE.AUTO_INSERT,
        source: 'profile',
        capability,
        host: normalizedHost,
        version: normalizedVersion,
        format: normalizedFormat,
      });
    }

    if (capability.transportFields.length > 0) {
      return this.#decorateResolution({
        mode: MODE.DRAG_TO_TIMELINE,
        source: 'profile',
        capability,
        host: normalizedHost,
        version: normalizedVersion,
        format: normalizedFormat,
      });
    }

    return this.#decorateResolution({
      mode: MODE.MANUAL_IMPORT,
      source: 'profile',
      capability,
      host: normalizedHost,
      version: normalizedVersion,
      format: normalizedFormat,
    });
  }

  #decorateResolution({ mode, source, capability, host, version, format }) {
    const statusBadge =
      mode === MODE.AUTO_INSERT
        ? 'Auto Insert'
        : mode === MODE.DRAG_TO_TIMELINE
          ? 'Drag to Timeline'
          : 'Manual Import';

    const fallbackAction =
      mode === MODE.AUTO_INSERT
        ? { label: 'Switch to Drag to Timeline', targetMode: MODE.DRAG_TO_TIMELINE }
        : mode === MODE.DRAG_TO_TIMELINE
          ? { label: 'Use Manual Import', targetMode: MODE.MANUAL_IMPORT }
          : { label: 'Open Import Guide', targetMode: MODE.MANUAL_IMPORT };

    return {
      profileVersion: this.profileVersion,
      host,
      version,
      format,
      mode,
      statusBadge,
      fallbackAction,
      source,
      capability,
    };
  }
}

export { MODE, BUILTIN_PROFILES, DEFAULT_PROFILE_VERSION, MemoryOverrideStore };
