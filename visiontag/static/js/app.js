import { detectBatch, detectByUrl, detectSingle, fetchOperationalMetrics } from "./api.js";
import {
  CONFIG_PRESETS,
  DEFAULT_CONFIG,
  MAX_BATCH_FILES,
  MODES,
  STATUS_VARIANT,
} from "./constants.js";
import {
  clamp,
  computeTagDelta,
  fileNameList,
  flattenBatchTags,
  makeReportFilename,
  nowPtBr,
  safeArray,
  uniqueTags,
} from "./helpers.js";
import { clearHistory, loadHistory, loadPreferences, pushHistoryItem, savePreferences } from "./storage.js";
import { ui } from "./ui.js";

const savedPreferences = loadPreferences() || {};
const initialMode = savedPreferences.mode === MODES.batch ? MODES.batch : MODES.single;

function normalizeConfig(candidate) {
  return {
    conf: clamp(Number(candidate?.conf ?? DEFAULT_CONFIG.conf), 0.1, 0.95),
    maxTags: clamp(Number(candidate?.maxTags ?? DEFAULT_CONFIG.maxTags), 1, 25),
    minAreaPercent: clamp(Number(candidate?.minAreaPercent ?? DEFAULT_CONFIG.minAreaPercent), 0, 50),
    includePerson: Boolean(candidate?.includePerson ?? DEFAULT_CONFIG.includePerson),
    visualFilterPercent: clamp(Number(candidate?.visualFilterPercent ?? DEFAULT_CONFIG.visualFilterPercent), 0, 95),
    includeLabels: String(candidate?.includeLabels ?? DEFAULT_CONFIG.includeLabels ?? ""),
    excludeLabels: String(candidate?.excludeLabels ?? DEFAULT_CONFIG.excludeLabels ?? ""),
    apiKey: "",
  };
}

const state = {
  mode: initialMode,
  config: normalizeConfig(savedPreferences.config),
  selectedFile: null,
  batchFiles: [],
  previewUrl: null,
  singleResult: null,
  batchResult: null,
  operationalMetrics: null,
  tagDelta: null,
  previousSingleTags: [],
  history: loadHistory(),
  historyQuery: "",
  requestController: null,
};

function revokePreviewUrl() {
  if (state.previewUrl) {
    URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = null;
  }
}

function setPreviewFromFile(file) {
  revokePreviewUrl();
  if (!file) {
    ui.renderSinglePreview(null);
    return;
  }

  state.previewUrl = URL.createObjectURL(file);
  ui.renderSinglePreview(state.previewUrl);
}

function getCurrentAnalyzeLabel() {
  return state.mode === MODES.single ? "Analisar imagem" : "Analisar lote";
}

function applyModeUI() {
  ui.setMode(state.mode);
  ui.dom.analyzeBtn.dataset.baseLabel = getCurrentAnalyzeLabel();
  ui.dom.analyzeBtn.textContent = ui.dom.analyzeBtn.dataset.baseLabel;
}

function syncConfigUI() {
  ui.setFormValues(state.config);
}

function persistUserPreferences() {
  const persistedConfig = {
    ...state.config,
    apiKey: "",
  };
  savePreferences({
    mode: state.mode,
    config: persistedConfig,
  });
}

function updateInputPreviewAndQueue() {
  if (state.mode === MODES.single) {
    setPreviewFromFile(state.selectedFile);
    ui.renderFileQueue(state.selectedFile ? [state.selectedFile] : []);
    return;
  }

  setPreviewFromFile(state.batchFiles[0] || null);
  ui.renderFileQueue(state.batchFiles);
}

function getActiveTags() {
  if (state.mode === MODES.single) {
    return uniqueTags(safeArray(state.singleResult?.tags));
  }
  return uniqueTags(flattenBatchTags(state.batchResult));
}

function flattenBatchDetections(payload) {
  if (!payload || !Array.isArray(payload.items)) {
    return [];
  }

  const detections = payload.items.flatMap((item) => {
    if (!item.result || !Array.isArray(item.result.detections)) {
      return [];
    }

    return item.result.detections.map((detection) => ({
      label: `${detection.label} • ${item.filename}`,
      confidence: detection.confidence,
      bbox: detection.bbox,
    }));
  });

  return detections.slice(0, 150);
}

function computeSingleMetrics(payload) {
  const tags = uniqueTags(safeArray(payload?.tags));
  return {
    files: payload ? 1 : 0,
    detections: payload?.total_detections || 0,
    inference: payload?.inference_ms || 0,
    uniqueTags: tags.length,
  };
}

function computeBatchMetrics(payload) {
  if (!payload || !Array.isArray(payload.items)) {
    return { files: 0, detections: 0, inference: 0, uniqueTags: 0 };
  }

  const successful = payload.items.filter((item) => item.result);
  const totalDetections = successful.reduce((sum, item) => sum + (item.result?.total_detections || 0), 0);
  const totalInference = successful.reduce((sum, item) => sum + (item.result?.inference_ms || 0), 0);
  const avgInference = successful.length ? (totalInference / successful.length).toFixed(2) : 0;

  return {
    files: payload.items.length,
    detections: totalDetections,
    inference: avgInference,
    uniqueTags: uniqueTags(flattenBatchTags(payload)).length,
  };
}

function renderResultSurface() {
  const minConfidence = state.config.visualFilterPercent;

  if (state.mode === MODES.single && state.singleResult) {
    ui.renderTags(safeArray(state.singleResult.tags));
    ui.renderTagDelta(state.tagDelta);
    ui.renderDetections(safeArray(state.singleResult.detections), minConfidence);
    ui.setMetrics(computeSingleMetrics(state.singleResult));
    ui.renderBatchResults(state.batchResult);
    return;
  }

  if (state.mode === MODES.batch && state.batchResult) {
    ui.renderTags(getActiveTags());
    ui.renderTagDelta(null);
    ui.renderDetections(flattenBatchDetections(state.batchResult), minConfidence);
    ui.setMetrics(computeBatchMetrics(state.batchResult));
    ui.renderBatchResults(state.batchResult);
    return;
  }

  ui.renderTags([]);
  ui.renderTagDelta(null);
  ui.renderDetections([], minConfidence);
  ui.setMetrics({ files: 0, detections: 0, inference: 0, uniqueTags: 0 });
  ui.renderBatchResults(state.batchResult);
}

function refreshActionAvailability() {
  const tags = getActiveTags();
  const canExport = Boolean(
    (state.mode === MODES.single && state.singleResult) ||
      (state.mode === MODES.batch && state.batchResult)
  );

  ui.setActionAvailability({ canExport, canCopy: tags.length > 0 });
}

function filteredHistoryEntries() {
  const query = state.historyQuery.trim().toLowerCase();
  if (!query) {
    return state.history;
  }

  return state.history.filter((item) => {
    const haystack = [
      item.fileName,
      item.mode,
      item.at,
      ...safeArray(item.tags),
      ...safeArray(item.files),
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
}

function renderHistory() {
  ui.renderHistory(filteredHistoryEntries());
}

function pushSingleHistory(payload) {
  const imageUrl = String(ui.dom.imageUrl.value || "").trim();
  const fileName = state.selectedFile?.name || (imageUrl ? `URL: ${imageUrl}` : "arquivo");
  const entry = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    at: nowPtBr(),
    mode: MODES.single,
    fileName,
    fileCount: 1,
    files: [fileName],
    tags: safeArray(payload.tags),
    totalDetections: payload.total_detections || 0,
    inferenceMs: payload.inference_ms || 0,
  };

  state.history = pushHistoryItem(state.history, entry);
  renderHistory();
}

function pushBatchHistory(payload) {
  const successful = safeArray(payload.items).filter((item) => item.result);
  const totalDetections = successful.reduce((sum, item) => sum + (item.result?.total_detections || 0), 0);
  const totalInference = successful.reduce((sum, item) => sum + (item.result?.inference_ms || 0), 0);
  const averageInference = successful.length ? Number((totalInference / successful.length).toFixed(2)) : 0;

  const entry = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    at: nowPtBr(),
    mode: MODES.batch,
    fileName: `Lote (${state.batchFiles.length} arquivos)`,
    fileCount: state.batchFiles.length,
    files: fileNameList(state.batchFiles),
    tags: uniqueTags(flattenBatchTags(payload)),
    totalDetections,
    inferenceMs: averageInference,
  };

  state.history = pushHistoryItem(state.history, entry);
  renderHistory();
}

function setStatus(message, variant) {
  ui.setStatus(message, variant);
}

function clearCurrentSelection() {
  state.selectedFile = null;
  state.batchFiles = [];
  ui.dom.fileInput.value = "";
  ui.dom.imageUrl.value = "";
  updateInputPreviewAndQueue();
}

function clearResults() {
  state.singleResult = null;
  state.batchResult = null;
  state.tagDelta = null;
  renderResultSurface();
  refreshActionAvailability();
}

function sanitizeIncomingFiles(fileList) {
  const all = Array.from(fileList || []);
  const images = all.filter((file) => file.type.startsWith("image/"));
  return images;
}

function assignFiles(files) {
  const incoming = sanitizeIncomingFiles(files);
  if (!incoming.length) {
    setStatus("Nenhum arquivo de imagem válido foi selecionado.", STATUS_VARIANT.error);
    return;
  }

  if (state.mode === MODES.single) {
    state.selectedFile = incoming[0];
    state.batchFiles = [];
    setStatus(`Arquivo pronto: ${state.selectedFile.name}`, STATUS_VARIANT.neutral);
  } else {
    state.batchFiles = incoming.slice(0, MAX_BATCH_FILES);
    state.selectedFile = null;
    const limitNote = incoming.length > MAX_BATCH_FILES ? ` (limitado a ${MAX_BATCH_FILES})` : "";
    setStatus(`${state.batchFiles.length} arquivos prontos para análise${limitNote}.`, STATUS_VARIANT.neutral);
  }

  updateInputPreviewAndQueue();
}

function switchMode(mode) {
  state.mode = mode;

  if (mode === MODES.single && state.batchFiles.length > 0) {
    state.selectedFile = state.batchFiles[0];
    state.batchFiles = [];
  }

  if (mode === MODES.batch && state.selectedFile) {
    state.batchFiles = [state.selectedFile];
    state.selectedFile = null;
  }

  applyModeUI();
  updateInputPreviewAndQueue();
  renderResultSurface();
  refreshActionAvailability();
  persistUserPreferences();
}

function copyCurrentTags() {
  const tags = getActiveTags();
  if (!tags.length) {
    setStatus("Não há tags disponíveis para copiar.", STATUS_VARIANT.error);
    return;
  }

  navigator.clipboard
    .writeText(tags.join(", "))
    .then(() => setStatus("Tags copiadas para a área de transferência.", STATUS_VARIANT.success))
    .catch(() => setStatus("Falha ao copiar tags automaticamente.", STATUS_VARIANT.error));
}

function exportCurrentReport() {
  const payload =
    state.mode === MODES.single
      ? {
          mode: MODES.single,
          generatedAt: new Date().toISOString(),
          fileName: state.selectedFile?.name || null,
          config: state.config,
          result: state.singleResult,
        }
      : {
          mode: MODES.batch,
          generatedAt: new Date().toISOString(),
          files: fileNameList(state.batchFiles),
          config: state.config,
          result: state.batchResult,
        };

  if (!payload.result) {
    setStatus("Não há resultado para exportar.", STATUS_VARIANT.error);
    return;
  }

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = makeReportFilename();
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  setStatus("Relatório JSON exportado com sucesso.", STATUS_VARIANT.success);
}

async function runAnalysis() {
  if (state.requestController) {
    state.requestController.abort();
  }

  const imageUrl = String(ui.dom.imageUrl.value || "").trim();

  if (state.mode === MODES.single && !state.selectedFile && !imageUrl) {
    setStatus("Selecione uma imagem ou informe uma URL para analisar.", STATUS_VARIANT.error);
    return;
  }

  if (state.mode === MODES.batch && state.batchFiles.length === 0) {
    setStatus("Selecione pelo menos uma imagem para análise em lote.", STATUS_VARIANT.error);
    return;
  }

  const controller = new AbortController();
  state.requestController = controller;

  ui.setLoading(true);
  setStatus("Análise em andamento...", STATUS_VARIANT.loading);

  try {
    if (state.mode === MODES.single) {
      const previousTags = uniqueTags(
        safeArray(state.previousSingleTags.length ? state.previousSingleTags : state.singleResult?.tags)
      );
      const payload = state.selectedFile
        ? await detectSingle(state.selectedFile, state.config, controller.signal)
        : await detectByUrl(imageUrl, state.config, controller.signal);
      state.singleResult = payload;
      state.tagDelta = computeTagDelta(previousTags, payload.tags);
      state.previousSingleTags = uniqueTags(safeArray(payload.tags));
      pushSingleHistory(payload);
      setStatus("Análise concluída com sucesso.", STATUS_VARIANT.success);
    } else {
      const payload = await detectBatch(state.batchFiles, state.config, controller.signal);
      state.batchResult = payload;
      state.tagDelta = null;
      pushBatchHistory(payload);
      setStatus("Análise em lote concluída.", STATUS_VARIANT.success);
    }
  } catch (error) {
    if (error?.name === "AbortError") {
      setStatus("Solicitação anterior cancelada.", STATUS_VARIANT.neutral);
    } else {
      setStatus(error?.message || "Falha ao processar a solicitação.", STATUS_VARIANT.error);
    }
  } finally {
    ui.setLoading(false);
    applyModeUI();
    state.requestController = null;
    renderResultSurface();
    refreshActionAvailability();
  }
}

function clearAll() {
  clearCurrentSelection();
  clearResults();
  setStatus("Interface limpa e pronta para nova análise.", STATUS_VARIANT.neutral);
}

async function loadMetrics() {
  const controller = new AbortController();
  try {
    setStatus("Consultando métricas operacionais...", STATUS_VARIANT.loading);
    const payload = await fetchOperationalMetrics(state.config, controller.signal);
    state.operationalMetrics = payload;
    ui.renderOperationalMetrics(payload);
    setStatus("Métricas atualizadas.", STATUS_VARIANT.success);
  } catch (error) {
    setStatus(error?.message || "Falha ao carregar métricas.", STATUS_VARIANT.error);
  }
}

function updateConfigFromForm() {
  state.config.conf = clamp(Number(ui.dom.confRange.value), 0.1, 0.95);
  state.config.maxTags = clamp(Number(ui.dom.maxTags.value) || 5, 1, 25);
  state.config.minAreaPercent = clamp(Number(ui.dom.minArea.value) || 1, 0, 50);
  state.config.includePerson = Boolean(ui.dom.includePerson.checked);
  state.config.visualFilterPercent = clamp(Number(ui.dom.filterRange.value) || 0, 0, 95);
  state.config.includeLabels = String(ui.dom.includeLabels.value || "");
  state.config.excludeLabels = String(ui.dom.excludeLabels.value || "");
  state.config.apiKey = String(ui.dom.apiKeyInput.value || "");

  syncConfigUI();
  renderResultSurface();
  persistUserPreferences();
}

function bindDropzoneEvents() {
  const activateDrag = (event) => {
    event.preventDefault();
    ui.dom.dropzone.classList.add("is-dragging");
  };

  const deactivateDrag = (event) => {
    event.preventDefault();
    ui.dom.dropzone.classList.remove("is-dragging");
  };

  ["dragenter", "dragover"].forEach((eventName) => ui.dom.dropzone.addEventListener(eventName, activateDrag));
  ["dragleave", "drop"].forEach((eventName) => ui.dom.dropzone.addEventListener(eventName, deactivateDrag));

  ui.dom.dropzone.addEventListener("drop", (event) => {
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      assignFiles(files);
    }
  });

  ui.dom.dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      ui.dom.fileInput.click();
    }
  });
}

function applyPreset(presetKey) {
  const preset = CONFIG_PRESETS[presetKey];
  if (!preset) {
    return;
  }

  state.config = {
    ...state.config,
    conf: preset.conf,
    maxTags: preset.maxTags,
    minAreaPercent: preset.minAreaPercent,
    includePerson: preset.includePerson,
  };

  syncConfigUI();
  renderResultSurface();
  persistUserPreferences();
  setStatus(`Preset aplicado: ${preset.label}.`, STATUS_VARIANT.neutral);
}

function isTypingContext(target) {
  if (!target || !(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select";
}

function bindGlobalShortcuts() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      ui.closeShortcuts();
      return;
    }

    if (!event.ctrlKey && event.key === "?") {
      event.preventDefault();
      ui.openShortcuts();
      return;
    }

    const typing = isTypingContext(event.target);

    if (event.ctrlKey && event.key === "Enter") {
      event.preventDefault();
      runAnalysis();
      return;
    }

    if (event.ctrlKey && (event.key === "k" || event.key === "K")) {
      event.preventDefault();
      ui.focusHistorySearch();
      return;
    }

    if (event.ctrlKey && (event.key === "b" || event.key === "B")) {
      event.preventDefault();
      const nextMode = state.mode === MODES.single ? MODES.batch : MODES.single;
      switchMode(nextMode);
      return;
    }

    if (typing) {
      return;
    }
  });
}

function bindEvents() {
  ui.dom.modeSingleBtn.addEventListener("click", () => switchMode(MODES.single));
  ui.dom.modeBatchBtn.addEventListener("click", () => switchMode(MODES.batch));

  ui.dom.presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyPreset(button.dataset.preset);
    });
  });

  ui.dom.fileInput.addEventListener("change", (event) => {
    assignFiles(event.target.files);
  });

  ui.dom.confRange.addEventListener("input", updateConfigFromForm);
  ui.dom.maxTags.addEventListener("change", updateConfigFromForm);
  ui.dom.minArea.addEventListener("change", updateConfigFromForm);
  ui.dom.includePerson.addEventListener("change", updateConfigFromForm);
  ui.dom.filterRange.addEventListener("input", updateConfigFromForm);
  ui.dom.includeLabels.addEventListener("change", updateConfigFromForm);
  ui.dom.excludeLabels.addEventListener("change", updateConfigFromForm);
  ui.dom.apiKeyInput.addEventListener("change", updateConfigFromForm);

  ui.dom.analyzeBtn.addEventListener("click", runAnalysis);
  ui.dom.copyTagsBtn.addEventListener("click", copyCurrentTags);
  ui.dom.downloadBtn.addEventListener("click", exportCurrentReport);
  ui.dom.clearBtn.addEventListener("click", clearAll);
  ui.dom.openShortcutsBtn.addEventListener("click", ui.openShortcuts);
  ui.dom.closeShortcutsBtn.addEventListener("click", ui.closeShortcuts);
  ui.dom.refreshMetricsBtn.addEventListener("click", loadMetrics);

  ui.dom.historySearch.addEventListener("input", (event) => {
    state.historyQuery = event.target.value || "";
    renderHistory();
  });

  ui.dom.clearHistoryBtn.addEventListener("click", () => {
    state.history = [];
    clearHistory();
    renderHistory();
    setStatus("Histórico local removido.", STATUS_VARIANT.neutral);
  });

  bindDropzoneEvents();
  bindGlobalShortcuts();
}

function init() {
  applyModeUI();
  syncConfigUI();
  updateInputPreviewAndQueue();
  renderResultSurface();
  ui.renderOperationalMetrics(state.operationalMetrics);
  renderHistory();
  refreshActionAvailability();
  setStatus("Selecione uma imagem para iniciar a análise.", STATUS_VARIANT.neutral);
  bindEvents();
}

init();
