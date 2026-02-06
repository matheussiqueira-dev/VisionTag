export const API_ROUTES = {
  detectSingle: "/api/v1/detect",
  detectBatch: "/api/v1/detect/batch",
};

export const MODES = {
  single: "single",
  batch: "batch",
};

export const HISTORY_KEY = "visiontag:history:v2";
export const MAX_HISTORY_ITEMS = 20;
export const MAX_BATCH_FILES = 12;

export const STATUS_VARIANT = {
  neutral: "neutral",
  loading: "loading",
  success: "success",
  error: "error",
};

export const DEFAULT_CONFIG = {
  conf: 0.7,
  maxTags: 5,
  minAreaPercent: 1,
  includePerson: false,
  visualFilterPercent: 0,
};
