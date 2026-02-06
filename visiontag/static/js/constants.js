export const API_ROUTES = {
  detectSingle: "/api/v1/detect",
  detectBatch: "/api/v1/detect/batch",
  detectUrl: "/api/v1/detect/url",
  metrics: "/api/v1/metrics",
  adminOverview: "/api/v1/admin/overview",
  adminCache: "/api/v1/admin/cache",
};

export const MODES = {
  single: "single",
  batch: "batch",
};

export const HISTORY_KEY = "visiontag:history:v2";
export const PREFERENCES_KEY = "visiontag:preferences:v1";
export const CUSTOM_PRESETS_KEY = "visiontag:custom-presets:v1";
export const UI_SETTINGS_KEY = "visiontag:ui-settings:v1";
export const MAX_HISTORY_ITEMS = 20;
export const MAX_BATCH_FILES = 12;
export const MAX_CUSTOM_PRESETS = 8;

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
  includeLabels: "",
  excludeLabels: "",
  apiKey: "",
};

export const CONFIG_PRESETS = {
  balanced: {
    label: "Balanceado",
    conf: 0.7,
    maxTags: 5,
    minAreaPercent: 1,
    includePerson: false,
  },
  highPrecision: {
    label: "Alta precisão",
    conf: 0.82,
    maxTags: 4,
    minAreaPercent: 2.2,
    includePerson: false,
  },
  sensitivity: {
    label: "Sensível",
    conf: 0.55,
    maxTags: 10,
    minAreaPercent: 0.5,
    includePerson: true,
  },
};
