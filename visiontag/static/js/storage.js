import {
  CUSTOM_PRESETS_KEY,
  HISTORY_KEY,
  MAX_CUSTOM_PRESETS,
  MAX_HISTORY_ITEMS,
  PREFERENCES_KEY,
  UI_SETTINGS_KEY,
} from "./constants.js";

export function loadHistory() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed;
  } catch {
    return [];
  }
}

export function persistHistory(items) {
  const safeItems = Array.isArray(items) ? items.slice(0, MAX_HISTORY_ITEMS) : [];
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(safeItems));
}

export function pushHistoryItem(history, entry) {
  const next = [entry, ...history].slice(0, MAX_HISTORY_ITEMS);
  persistHistory(next);
  return next;
}

export function clearHistory() {
  window.localStorage.removeItem(HISTORY_KEY);
}

export function loadPreferences() {
  try {
    const raw = window.localStorage.getItem(PREFERENCES_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed ? parsed : null;
  } catch {
    return null;
  }
}

export function savePreferences(preferences) {
  if (!preferences || typeof preferences !== "object") {
    return;
  }
  window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
}

export function loadCustomPresets() {
  try {
    const raw = window.localStorage.getItem(CUSTOM_PRESETS_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.slice(0, MAX_CUSTOM_PRESETS).filter((item) => item && typeof item === "object");
  } catch {
    return [];
  }
}

export function saveCustomPresets(presets) {
  const safePresets = Array.isArray(presets) ? presets.slice(0, MAX_CUSTOM_PRESETS) : [];
  window.localStorage.setItem(CUSTOM_PRESETS_KEY, JSON.stringify(safePresets));
}

export function loadUiSettings() {
  try {
    const raw = window.localStorage.getItem(UI_SETTINGS_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function saveUiSettings(settings) {
  if (!settings || typeof settings !== "object") {
    return;
  }
  window.localStorage.setItem(UI_SETTINGS_KEY, JSON.stringify(settings));
}
