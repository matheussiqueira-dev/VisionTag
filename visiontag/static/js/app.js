import { detectBatch, detectSingle } from "./api.js";
import {
  DEFAULT_CONFIG,
  MAX_BATCH_FILES,
  MODES,
  STATUS_VARIANT,
} from "./constants.js";
import {
  clamp,
  fileNameList,
  flattenBatchTags,
  makeReportFilename,
  nowPtBr,
  safeArray,
  uniqueTags,
} from "./helpers.js";
import { clearHistory, loadHistory, pushHistoryItem } from "./storage.js";
import { ui } from "./ui.js";

const state = {
  mode: MODES.single,
  config: { ...DEFAULT_CONFIG },
  selectedFile: null,
  batchFiles: [],
  previewUrl: null,
  singleResult: null,
  batchResult: null,
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
    ui.renderDetections(safeArray(state.singleResult.detections), minConfidence);
    ui.setMetrics(computeSingleMetrics(state.singleResult));
    ui.renderBatchResults(state.batchResult);
    return;
  }

  if (state.mode === MODES.batch && state.batchResult) {
    ui.renderTags(getActiveTags());
    ui.renderDetections(flattenBatchDetections(state.batchResult), minConfidence);
    ui.setMetrics(computeBatchMetrics(state.batchResult));
    ui.renderBatchResults(state.batchResult);
    return;
  }

  ui.renderTags([]);
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
  const entry = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    at: nowPtBr(),
    mode: MODES.single,
    fileName: state.selectedFile?.name || "arquivo",
    fileCount: 1,
    files: [state.selectedFile?.name || "arquivo"],
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
  updateInputPreviewAndQueue();
}

function clearResults() {
  state.singleResult = null;
  state.batchResult = null;
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

  if (state.mode === MODES.single && !state.selectedFile) {
    setStatus("Selecione uma imagem antes de analisar.", STATUS_VARIANT.error);
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
      const payload = await detectSingle(state.selectedFile, state.config, controller.signal);
      state.singleResult = payload;
      pushSingleHistory(payload);
      setStatus("Análise concluída com sucesso.", STATUS_VARIANT.success);
    } else {
      const payload = await detectBatch(state.batchFiles, state.config, controller.signal);
      state.batchResult = payload;
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

function updateConfigFromForm() {
  state.config.conf = clamp(Number(ui.dom.confRange.value), 0.1, 0.95);
  state.config.maxTags = clamp(Number(ui.dom.maxTags.value) || 5, 1, 25);
  state.config.minAreaPercent = clamp(Number(ui.dom.minArea.value) || 1, 0, 50);
  state.config.includePerson = Boolean(ui.dom.includePerson.checked);
  state.config.visualFilterPercent = clamp(Number(ui.dom.filterRange.value) || 0, 0, 95);

  syncConfigUI();
  renderResultSurface();
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

function bindEvents() {
  ui.dom.modeSingleBtn.addEventListener("click", () => switchMode(MODES.single));
  ui.dom.modeBatchBtn.addEventListener("click", () => switchMode(MODES.batch));

  ui.dom.fileInput.addEventListener("change", (event) => {
    assignFiles(event.target.files);
  });

  ui.dom.confRange.addEventListener("input", updateConfigFromForm);
  ui.dom.maxTags.addEventListener("change", updateConfigFromForm);
  ui.dom.minArea.addEventListener("change", updateConfigFromForm);
  ui.dom.includePerson.addEventListener("change", updateConfigFromForm);
  ui.dom.filterRange.addEventListener("input", updateConfigFromForm);

  ui.dom.analyzeBtn.addEventListener("click", runAnalysis);
  ui.dom.copyTagsBtn.addEventListener("click", copyCurrentTags);
  ui.dom.downloadBtn.addEventListener("click", exportCurrentReport);
  ui.dom.clearBtn.addEventListener("click", clearAll);

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
}

function init() {
  applyModeUI();
  syncConfigUI();
  updateInputPreviewAndQueue();
  renderResultSurface();
  renderHistory();
  refreshActionAvailability();
  setStatus("Selecione uma imagem para iniciar a análise.", STATUS_VARIANT.neutral);
  bindEvents();
}

init();
