export function bytesToReadable(size) {
  if (!Number.isFinite(size) || size <= 0) {
    return "0 KB";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unit = units[0];

  for (const current of units) {
    unit = current;
    if (value < 1024 || current === units[units.length - 1]) {
      break;
    }
    value /= 1024;
  }

  const precision = value < 10 ? 1 : 0;
  return `${value.toFixed(precision)} ${unit}`;
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function toPercent(value) {
  const safe = Number.isFinite(value) ? value : 0;
  return `${(safe * 100).toFixed(1)}%`;
}

export function nowPtBr() {
  return new Date().toLocaleString("pt-BR");
}

export function uniqueTags(tags) {
  return Array.from(new Set(tags.filter(Boolean)));
}

export function fileNameList(files) {
  return files.map((file) => file.name);
}

export function flattenBatchTags(batchPayload) {
  if (!batchPayload || !Array.isArray(batchPayload.items)) {
    return [];
  }

  return batchPayload.items
    .filter((item) => item.result && Array.isArray(item.result.tags))
    .flatMap((item) => item.result.tags);
}

export function makeReportFilename() {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `visiontag-relatorio-${stamp}.json`;
}

export function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

export function computeTagDelta(previousTags, currentTags) {
  const prev = new Set(safeArray(previousTags));
  const curr = new Set(safeArray(currentTags));

  const added = Array.from(curr).filter((tag) => !prev.has(tag));
  const removed = Array.from(prev).filter((tag) => !curr.has(tag));
  const kept = Array.from(curr).filter((tag) => prev.has(tag));

  return { added, removed, kept };
}

export function debounce(fn, waitMs = 180) {
  let timeoutId = null;
  return (...args) => {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
    timeoutId = window.setTimeout(() => {
      fn(...args);
    }, waitMs);
  };
}

export function detectionInsights(detections) {
  const items = safeArray(detections).filter((item) => item && Number.isFinite(Number(item.confidence)));
  if (!items.length) {
    return {
      total: 0,
      averageConfidence: 0,
      highestConfidence: 0,
      uniqueLabels: 0,
      topLabels: [],
    };
  }

  const byLabel = new Map();
  let confidenceTotal = 0;
  let highestConfidence = 0;
  for (const item of items) {
    const label = String(item.label || "objeto");
    const confidence = Number(item.confidence) || 0;
    confidenceTotal += confidence;
    highestConfidence = Math.max(highestConfidence, confidence);
    const previous = byLabel.get(label) || { count: 0, maxConfidence: 0 };
    byLabel.set(label, {
      count: previous.count + 1,
      maxConfidence: Math.max(previous.maxConfidence, confidence),
    });
  }

  const topLabels = Array.from(byLabel.entries())
    .map(([label, meta]) => ({
      label,
      count: meta.count,
      maxConfidence: meta.maxConfidence,
    }))
    .sort((a, b) => b.count - a.count || b.maxConfidence - a.maxConfidence)
    .slice(0, 6);

  return {
    total: items.length,
    averageConfidence: confidenceTotal / items.length,
    highestConfidence,
    uniqueLabels: byLabel.size,
    topLabels,
  };
}
