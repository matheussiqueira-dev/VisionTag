const HISTORY_KEY = "visiontag:history:v1";
const MAX_HISTORY_ITEMS = 12;

const elements = {
  dropzone: document.getElementById("dropzone"),
  imageInput: document.getElementById("imageInput"),
  preview: document.getElementById("preview"),
  confRange: document.getElementById("confRange"),
  confValue: document.getElementById("confValue"),
  maxTags: document.getElementById("maxTags"),
  minArea: document.getElementById("minArea"),
  includePerson: document.getElementById("includePerson"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  clearBtn: document.getElementById("clearBtn"),
  copyTagsBtn: document.getElementById("copyTagsBtn"),
  clearHistoryBtn: document.getElementById("clearHistoryBtn"),
  statusMessage: document.getElementById("statusMessage"),
  tagsWrap: document.getElementById("tagsWrap"),
  detectionsBody: document.getElementById("detectionsBody"),
  metricDetections: document.getElementById("metricDetections"),
  metricInference: document.getElementById("metricInference"),
  metricUnique: document.getElementById("metricUnique"),
  historyList: document.getElementById("historyList"),
};

const state = {
  selectedFile: null,
  latestTags: [],
  history: loadHistory(),
};

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function persistHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history.slice(0, MAX_HISTORY_ITEMS)));
}

function setStatus(message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "var(--danger)" : "var(--text-muted)";
}

function resetResults() {
  elements.tagsWrap.className = "tags-empty";
  elements.tagsWrap.textContent = "As tags aparecerão aqui após a análise.";
  elements.detectionsBody.innerHTML = '<tr><td colspan="3" class="muted">Sem dados.</td></tr>';
  elements.metricDetections.textContent = "0";
  elements.metricInference.textContent = "0 ms";
  elements.metricUnique.textContent = "0";
  state.latestTags = [];
  elements.copyTagsBtn.disabled = true;
}

function renderPreview(file) {
  if (!file) {
    elements.preview.innerHTML = "<p>Nenhuma imagem selecionada.</p>";
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    elements.preview.innerHTML = `<img src="${reader.result}" alt="Pré-visualização da imagem selecionada" />`;
  };
  reader.readAsDataURL(file);
}

function formatBBox(bbox) {
  return `${bbox.x1}, ${bbox.y1}, ${bbox.x2}, ${bbox.y2}`;
}

function renderTags(tags) {
  if (!tags.length) {
    elements.tagsWrap.className = "tags-empty";
    elements.tagsWrap.textContent = "Nenhuma tag detectada nesta imagem.";
    return;
  }

  elements.tagsWrap.className = "tags-wrap";
  elements.tagsWrap.innerHTML = tags.map((tag) => `<span class="tag">${tag}</span>`).join("");
}

function renderDetections(detections) {
  if (!detections.length) {
    elements.detectionsBody.innerHTML = '<tr><td colspan="3" class="muted">Nenhuma detecção acima dos critérios atuais.</td></tr>';
    return;
  }

  elements.detectionsBody.innerHTML = detections
    .map(
      (item) =>
        `<tr>
          <td>${item.label}</td>
          <td>${(item.confidence * 100).toFixed(1)}%</td>
          <td>${formatBBox(item.bbox)}</td>
        </tr>`
    )
    .join("");
}

function addHistoryEntry(fileName, payload) {
  const entry = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    at: new Date().toLocaleString("pt-BR"),
    fileName,
    tags: payload.tags,
    totalDetections: payload.total_detections,
    inferenceMs: payload.inference_ms,
  };

  state.history.unshift(entry);
  state.history = state.history.slice(0, MAX_HISTORY_ITEMS);
  persistHistory();
  renderHistory();
}

function renderHistory() {
  if (!state.history.length) {
    elements.historyList.innerHTML = '<li class="history-item"><span>Nenhuma análise registrada.</span></li>';
    return;
  }

  elements.historyList.innerHTML = state.history
    .map(
      (item) =>
        `<li class="history-item">
          <strong>${item.fileName}</strong>
          <span>${item.at} • ${item.totalDetections} detecções • ${item.inferenceMs ?? 0} ms</span>
          <div class="history-tags">
            ${item.tags.length ? item.tags.map((tag) => `<b>${tag}</b>`).join("") : "<span>Sem tags</span>"}
          </div>
        </li>`
    )
    .join("");
}

function getRequestConfig() {
  const conf = Number(elements.confRange.value);
  const maxTags = Number(elements.maxTags.value || 5);
  const minAreaPercent = Number(elements.minArea.value || 1.0);
  const includePerson = elements.includePerson.checked;

  return {
    conf,
    maxTags,
    minArea: minAreaPercent / 100,
    includePerson,
  };
}

function buildQueryParams(config) {
  const params = new URLSearchParams();
  params.set("conf", String(config.conf));
  params.set("max_tags", String(config.maxTags));
  params.set("min_area", String(config.minArea));
  params.set("include_person", String(config.includePerson));
  return params;
}

async function analyzeCurrentImage() {
  if (!state.selectedFile) {
    setStatus("Selecione uma imagem antes de analisar.", true);
    return;
  }

  const config = getRequestConfig();
  const query = buildQueryParams(config);
  const formData = new FormData();
  formData.append("file", state.selectedFile);

  elements.analyzeBtn.disabled = true;
  setStatus("Analisando imagem...");

  try {
    const response = await fetch(`/api/v1/detect?${query.toString()}`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      const error = payload && payload.detail ? payload.detail : "Erro inesperado durante a análise.";
      throw new Error(error);
    }

    renderTags(payload.tags || []);
    renderDetections(payload.detections || []);

    elements.metricDetections.textContent = String(payload.total_detections || 0);
    elements.metricInference.textContent = `${payload.inference_ms ?? 0} ms`;
    elements.metricUnique.textContent = String(new Set(payload.tags || []).size);

    state.latestTags = payload.tags || [];
    elements.copyTagsBtn.disabled = state.latestTags.length === 0;
    setStatus("Análise concluída com sucesso.");

    addHistoryEntry(state.selectedFile.name, payload);
  } catch (error) {
    setStatus(error.message || "Falha ao processar a imagem.", true);
  } finally {
    elements.analyzeBtn.disabled = false;
  }
}

function onFileSelected(file) {
  state.selectedFile = file || null;
  renderPreview(state.selectedFile);
  resetResults();
  if (state.selectedFile) {
    setStatus(`Arquivo pronto: ${state.selectedFile.name}`);
  } else {
    setStatus("Pronto para análise.");
  }
}

function setupDropzone() {
  const dragEvents = ["dragenter", "dragover"];
  dragEvents.forEach((eventName) => {
    elements.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropzone.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    elements.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropzone.classList.remove("is-dragging");
    });
  });

  elements.dropzone.addEventListener("drop", (event) => {
    const files = event.dataTransfer?.files;
    if (!files || !files.length) return;
    onFileSelected(files[0]);
  });
}

function bindEvents() {
  elements.imageInput.addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    onFileSelected(file || null);
  });

  elements.confRange.addEventListener("input", () => {
    elements.confValue.textContent = Number(elements.confRange.value).toFixed(2);
  });

  elements.analyzeBtn.addEventListener("click", analyzeCurrentImage);

  elements.clearBtn.addEventListener("click", () => {
    elements.imageInput.value = "";
    onFileSelected(null);
  });

  elements.copyTagsBtn.addEventListener("click", async () => {
    if (!state.latestTags.length) return;
    const value = state.latestTags.join(", ");
    try {
      await navigator.clipboard.writeText(value);
      setStatus("Tags copiadas para a área de transferência.");
    } catch {
      setStatus("Não foi possível copiar automaticamente.", true);
    }
  });

  elements.clearHistoryBtn.addEventListener("click", () => {
    state.history = [];
    persistHistory();
    renderHistory();
    setStatus("Histórico local removido.");
  });
}

function init() {
  elements.confValue.textContent = Number(elements.confRange.value).toFixed(2);
  setupDropzone();
  bindEvents();
  renderHistory();
  resetResults();
}

init();
