const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const selectedFilesEl = document.getElementById("selectedFiles");
const analyzeButton = document.getElementById("analyzeButton");
const emptyState = document.getElementById("emptyState");
const loadingState = document.getElementById("loadingState");
const resultContainer = document.getElementById("resultContainer");
const resultTemplate = document.getElementById("resultTemplate");
const healthBadge = document.getElementById("healthBadge");

const confInput = document.getElementById("confInput");
const maxTagsInput = document.getElementById("maxTagsInput");
const minAreaInput = document.getElementById("minAreaInput");
const apiKeyInput = document.getElementById("apiKeyInput");
const includePersonInput = document.getElementById("includePersonInput");
const includeDetailsInput = document.getElementById("includeDetailsInput");

let selectedFiles = [];

function setFiles(fileList) {
  selectedFiles = Array.from(fileList || []);
  if (!selectedFiles.length) {
    selectedFilesEl.textContent = "Nenhum arquivo selecionado.";
    return;
  }
  const fragments = selectedFiles.map((file) => {
    const span = document.createElement("span");
    span.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    return span;
  });
  selectedFilesEl.replaceChildren(...fragments);
}

function showLoading(isLoading) {
  loadingState.hidden = !isLoading;
  analyzeButton.disabled = isLoading;
}

function clearResults() {
  resultContainer.innerHTML = "";
  emptyState.hidden = false;
}

function appendResultCard(title, tags, payload) {
  const fragment = resultTemplate.content.cloneNode(true);
  fragment.querySelector(".result-title").textContent = title;
  fragment.querySelector(".result-tags").textContent = tags.length
    ? `Tags: ${tags.join(", ")}`
    : "Sem tags";
  fragment.querySelector(".result-json").textContent = JSON.stringify(payload, null, 2);
  resultContainer.appendChild(fragment);
}

function getHeaders() {
  const headers = {};
  const apiKey = apiKeyInput.value.trim();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

function buildQueryParams() {
  const params = new URLSearchParams({
    conf: confInput.value || "0.7",
    max_tags: maxTagsInput.value || "5",
    min_area: minAreaInput.value || "0.01",
    include_person: String(includePersonInput.checked),
    include_details: String(includeDetailsInput.checked),
  });
  return params.toString();
}

async function analyzeSingle(file) {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`/api/v1/detect?${buildQueryParams()}`, {
    method: "POST",
    headers: getHeaders(),
    body: form,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Falha ao detectar imagem.");
  }
  return payload;
}

async function analyzeBatch(files) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const response = await fetch(`/api/v1/detect/batch?${buildQueryParams()}`, {
    method: "POST",
    headers: getHeaders(),
    body: form,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Falha ao detectar lote de imagens.");
  }
  return payload;
}

async function runAnalysis() {
  if (!selectedFiles.length) {
    selectedFilesEl.textContent = "Selecione ao menos uma imagem antes de analisar.";
    return;
  }

  emptyState.hidden = true;
  resultContainer.innerHTML = "";
  showLoading(true);

  try {
    if (selectedFiles.length === 1) {
      const payload = await analyzeSingle(selectedFiles[0]);
      appendResultCard(selectedFiles[0].name, payload.tags || [], payload);
      return;
    }

    const payload = await analyzeBatch(selectedFiles);
    payload.items.forEach((item) => {
      appendResultCard(item.filename, item.tags || [], item);
    });
  } catch (error) {
    appendResultCard("Erro", [], { detail: error.message });
  } finally {
    showLoading(false);
  }
}

async function loadHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("API indisponível");
    }
    const payload = await response.json();
    healthBadge.textContent = `API online • modelo ${payload.model}`;
  } catch (_) {
    healthBadge.textContent = "API offline";
  }
}

async function loadDefaults() {
  try {
    const response = await fetch("/api/v1/config");
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    confInput.value = String(payload.defaults.conf);
    maxTagsInput.value = String(payload.defaults.max_tags);
    minAreaInput.value = String(payload.defaults.min_area);
    includePersonInput.checked = Boolean(payload.defaults.include_person);
  } catch (_) {
    // Mantem defaults do formulario quando endpoint estiver indisponivel.
  }
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("drag-active");
});
dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("drag-active");
});
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("drag-active");
  setFiles(event.dataTransfer.files);
});

fileInput.addEventListener("change", () => setFiles(fileInput.files));
analyzeButton.addEventListener("click", runAnalysis);

clearResults();
setFiles([]);
loadHealth();
loadDefaults();
