import { HISTORY_KEY, MAX_HISTORY_ITEMS } from "./constants.js";

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
