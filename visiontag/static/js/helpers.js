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
