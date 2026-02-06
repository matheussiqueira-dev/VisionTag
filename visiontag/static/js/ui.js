import { MODES, STATUS_VARIANT } from "./constants.js";
import { bytesToReadable, safeArray, toPercent } from "./helpers.js";

const dom = {
  modeSingleBtn: document.getElementById("modeSingleBtn"),
  modeBatchBtn: document.getElementById("modeBatchBtn"),
  modeHint: document.getElementById("modeHint"),
  journeySteps: document.getElementById("journeySteps"),
  contextSummary: document.getElementById("contextSummary"),
  preflightBadge: document.getElementById("preflightBadge"),
  preflightList: document.getElementById("preflightList"),
  quickSingleBtn: document.getElementById("quickSingleBtn"),
  quickBatchFilesBtn: document.getElementById("quickBatchFilesBtn"),
  quickBatchUrlsBtn: document.getElementById("quickBatchUrlsBtn"),
  batchSourceFilesBtn: document.getElementById("batchSourceFilesBtn"),
  batchSourceUrlsBtn: document.getElementById("batchSourceUrlsBtn"),
  batchSourceHint: document.getElementById("batchSourceHint"),
  presetButtons: Array.from(document.querySelectorAll(".preset-btn")),
  toggleContrastBtn: document.getElementById("toggleContrastBtn"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("fileInput"),
  dropzoneTitle: document.getElementById("dropzoneTitle"),
  fileHint: document.getElementById("fileHint"),
  previewPane: document.getElementById("previewPane"),
  fileQueue: document.getElementById("fileQueue"),
  batchUrlsInput: document.getElementById("batchUrlsInput"),

  confRange: document.getElementById("confRange"),
  confValue: document.getElementById("confValue"),
  maxTags: document.getElementById("maxTags"),
  minArea: document.getElementById("minArea"),
  includePerson: document.getElementById("includePerson"),
  filterRange: document.getElementById("filterRange"),
  filterValue: document.getElementById("filterValue"),
  includeLabels: document.getElementById("includeLabels"),
  excludeLabels: document.getElementById("excludeLabels"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  imageUrl: document.getElementById("imageUrl"),
  customPresetName: document.getElementById("customPresetName"),
  savePresetBtn: document.getElementById("savePresetBtn"),
  customPresetList: document.getElementById("customPresetList"),
  compactMode: document.getElementById("compactMode"),
  highContrastMode: document.getElementById("highContrastMode"),

  analyzeBtn: document.getElementById("analyzeBtn"),
  downloadBtn: document.getElementById("downloadBtn"),
  copyTagsBtn: document.getElementById("copyTagsBtn"),
  clearBtn: document.getElementById("clearBtn"),

  statusPill: document.getElementById("statusPill"),
  statusMessage: document.getElementById("statusMessage"),
  metricFiles: document.getElementById("metricFiles"),
  metricDetections: document.getElementById("metricDetections"),
  metricInference: document.getElementById("metricInference"),
  metricUnique: document.getElementById("metricUnique"),

  tagsWrap: document.getElementById("tagsWrap"),
  tagDeltaWrap: document.getElementById("tagDeltaWrap"),
  detectionsBody: document.getElementById("detectionsBody"),
  insightsPanel: document.getElementById("insightsPanel"),
  batchResults: document.getElementById("batchResults"),

  historySearch: document.getElementById("historySearch"),
  historyList: document.getElementById("historyList"),
  clearHistoryBtn: document.getElementById("clearHistoryBtn"),
  refreshMetricsBtn: document.getElementById("refreshMetricsBtn"),
  clearCacheBtn: document.getElementById("clearCacheBtn"),
  metricsPanel: document.getElementById("metricsPanel"),
  runtimePanel: document.getElementById("runtimePanel"),
  recentPanel: document.getElementById("recentPanel"),

  openShortcutsBtn: document.getElementById("openShortcutsBtn"),
  closeShortcutsBtn: document.getElementById("closeShortcutsBtn"),
  shortcutsDialog: document.getElementById("shortcutsDialog"),
};

function setText(element, value) {
  element.textContent = value;
}

function setStatusVariant(variant) {
  dom.statusPill.classList.remove("is-loading", "is-success", "is-error", "is-warning");

  if (variant === STATUS_VARIANT.loading) {
    dom.statusPill.classList.add("is-loading");
    setText(dom.statusPill, "Processando");
    return;
  }

  if (variant === STATUS_VARIANT.success) {
    dom.statusPill.classList.add("is-success");
    setText(dom.statusPill, "Concluído");
    return;
  }

  if (variant === STATUS_VARIANT.error) {
    dom.statusPill.classList.add("is-error");
    setText(dom.statusPill, "Erro");
    return;
  }

  if (variant === "warning") {
    dom.statusPill.classList.add("is-warning");
    setText(dom.statusPill, "Atenção");
    return;
  }

  setText(dom.statusPill, "Pronto");
}

function createTagChip(label) {
  const chip = document.createElement("span");
  chip.className = "tag-chip";
  chip.textContent = label;
  return chip;
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function renderSinglePreview(previewUrl) {
  clearElement(dom.previewPane);
  if (!previewUrl) {
    const placeholder = document.createElement("p");
    placeholder.textContent = "Sem imagem selecionada.";
    dom.previewPane.appendChild(placeholder);
    return;
  }

  const image = document.createElement("img");
  image.src = previewUrl;
  image.alt = "Pré-visualização da imagem selecionada";
  image.loading = "lazy";
  dom.previewPane.appendChild(image);
}

function renderFileQueue(files) {
  clearElement(dom.fileQueue);
  if (!files.length) {
    return;
  }

  const fragment = document.createDocumentFragment();
  files.forEach((file, index) => {
    const li = document.createElement("li");
    li.className = "file-item";

    const fileName = document.createElement("strong");
    fileName.textContent = `${index + 1}. ${file.name}`;

    const fileSize = document.createElement("span");
    fileSize.textContent = bytesToReadable(file.size);

    li.appendChild(fileName);
    li.appendChild(fileSize);
    fragment.appendChild(li);
  });

  dom.fileQueue.appendChild(fragment);
}

function renderUrlQueue(urls) {
  clearElement(dom.fileQueue);
  const entries = safeArray(urls).filter((url) => typeof url === "string" && url.trim());
  if (!entries.length) {
    return;
  }

  const fragment = document.createDocumentFragment();
  entries.forEach((url, index) => {
    const li = document.createElement("li");
    li.className = "file-item";

    const fileName = document.createElement("strong");
    fileName.textContent = `${index + 1}. ${url}`;

    const fileSize = document.createElement("span");
    fileSize.textContent = "URL";

    li.appendChild(fileName);
    li.appendChild(fileSize);
    fragment.appendChild(li);
  });
  dom.fileQueue.appendChild(fragment);
}

function renderTags(tags) {
  clearElement(dom.tagsWrap);

  if (!tags.length) {
    dom.tagsWrap.className = "tags-empty";
    setText(dom.tagsWrap, "Sem tags para exibir.");
    return;
  }

  dom.tagsWrap.className = "tags-wrap";
  const fragment = document.createDocumentFragment();
  tags.forEach((tag) => fragment.appendChild(createTagChip(tag)));
  dom.tagsWrap.appendChild(fragment);
}

function renderDetections(detections, minConfidencePercent) {
  clearElement(dom.detectionsBody);

  const filtered = safeArray(detections).filter(
    (item) => item && Number(item.confidence) * 100 >= minConfidencePercent
  );

  if (!filtered.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.className = "td-empty";
    cell.textContent = "Nenhuma detecção para os critérios atuais.";
    row.appendChild(cell);
    dom.detectionsBody.appendChild(row);
    return;
  }

  const fragment = document.createDocumentFragment();
  filtered.forEach((item) => {
    const row = document.createElement("tr");

    const labelCell = document.createElement("td");
    labelCell.textContent = item.label;

    const confidenceCell = document.createElement("td");
    confidenceCell.textContent = toPercent(item.confidence);

    const bboxCell = document.createElement("td");
    const bbox = item.bbox || {};
    bboxCell.textContent = `${bbox.x1}, ${bbox.y1}, ${bbox.x2}, ${bbox.y2}`;

    row.appendChild(labelCell);
    row.appendChild(confidenceCell);
    row.appendChild(bboxCell);
    fragment.appendChild(row);
  });

  dom.detectionsBody.appendChild(fragment);
}

function createDeltaCard({ title, className, tags, emptyMessage }) {
  const card = document.createElement("article");
  card.className = `delta-card ${className}`;

  const heading = document.createElement("strong");
  heading.textContent = title;
  card.appendChild(heading);

  const list = document.createElement("ul");
  if (!tags.length) {
    const li = document.createElement("li");
    li.textContent = emptyMessage;
    list.appendChild(li);
  } else {
    tags.slice(0, 8).forEach((tag) => {
      const li = document.createElement("li");
      li.textContent = tag;
      list.appendChild(li);
    });
  }

  card.appendChild(list);
  return card;
}

function renderTagDelta(delta) {
  clearElement(dom.tagDeltaWrap);

  if (!delta) {
    dom.tagDeltaWrap.className = "delta-empty";
    dom.tagDeltaWrap.textContent = "Sem comparação disponível.";
    return;
  }

  dom.tagDeltaWrap.className = "delta-grid";
  dom.tagDeltaWrap.appendChild(
    createDeltaCard({
      title: "Novas tags",
      className: "delta-card--added",
      tags: safeArray(delta.added),
      emptyMessage: "Nenhuma tag nova",
    })
  );
  dom.tagDeltaWrap.appendChild(
    createDeltaCard({
      title: "Removidas",
      className: "delta-card--removed",
      tags: safeArray(delta.removed),
      emptyMessage: "Nenhuma tag removida",
    })
  );
  dom.tagDeltaWrap.appendChild(
    createDeltaCard({
      title: "Mantidas",
      className: "delta-card--kept",
      tags: safeArray(delta.kept),
      emptyMessage: "Sem recorrência",
    })
  );
}

function makeBatchCard(item) {
  const card = document.createElement("article");
  card.className = "batch-card";

  const title = document.createElement("h5");
  title.textContent = item.filename || "arquivo";
  card.appendChild(title);

  if (item.error) {
    card.classList.add("is-error");
    const errorText = document.createElement("p");
    errorText.textContent = item.error;
    card.appendChild(errorText);
    return card;
  }

  const summaryText = document.createElement("p");
  const detections = item.result?.total_detections ?? 0;
  const inference = item.result?.inference_ms ?? 0;
  summaryText.textContent = `${detections} detecções • ${inference} ms`;
  card.appendChild(summaryText);

  const tagsWrap = document.createElement("div");
  tagsWrap.className = "batch-tags";
  safeArray(item.result?.tags).forEach((tag) => {
    const chip = document.createElement("span");
    chip.textContent = tag;
    tagsWrap.appendChild(chip);
  });

  if (!tagsWrap.childElementCount) {
    const noTags = document.createElement("p");
    noTags.textContent = "Sem tags.";
    card.appendChild(noTags);
  } else {
    card.appendChild(tagsWrap);
  }

  return card;
}

function renderBatchResults(batchPayload) {
  clearElement(dom.batchResults);

  if (!batchPayload || !Array.isArray(batchPayload.items) || !batchPayload.items.length) {
    dom.batchResults.className = "batch-empty";
    dom.batchResults.textContent = "Sem análises em lote até o momento.";
    return;
  }

  dom.batchResults.className = "batch-grid";
  const fragment = document.createDocumentFragment();
  batchPayload.items.forEach((item) => fragment.appendChild(makeBatchCard(item)));
  dom.batchResults.appendChild(fragment);
}

function renderInsights(insights) {
  clearElement(dom.insightsPanel);
  if (!insights || !insights.total) {
    dom.insightsPanel.className = "insights-empty";
    dom.insightsPanel.textContent = "Insights serão exibidos após a análise.";
    return;
  }

  dom.insightsPanel.className = "insights-grid";

  const summary = document.createElement("div");
  summary.className = "insights-summary";

  const cards = [
    ["Detecções", insights.total],
    ["Confiança média", `${(Number(insights.averageConfidence) * 100).toFixed(1)}%`],
    ["Pico de confiança", `${(Number(insights.highestConfidence) * 100).toFixed(1)}%`],
    ["Labels únicas", insights.uniqueLabels],
  ];

  cards.forEach(([label, value]) => {
    const card = document.createElement("article");
    card.className = "insight-kpi";
    const name = document.createElement("span");
    name.textContent = String(label);
    const amount = document.createElement("strong");
    amount.textContent = String(value);
    card.appendChild(name);
    card.appendChild(amount);
    summary.appendChild(card);
  });

  dom.insightsPanel.appendChild(summary);

  const bars = document.createElement("div");
  bars.className = "insight-bars";
  safeArray(insights.topLabels).forEach((item) => {
    const row = document.createElement("div");
    row.className = "insight-bar";

    const label = document.createElement("span");
    label.textContent = item.label;
    row.appendChild(label);

    const track = document.createElement("div");
    track.className = "insight-track";
    const fill = document.createElement("div");
    fill.className = "insight-fill";
    fill.style.width = `${Math.max(6, Math.round((Number(item.maxConfidence) || 0) * 100))}%`;
    track.appendChild(fill);
    row.appendChild(track);

    const meta = document.createElement("strong");
    meta.textContent = `${item.count}x`;
    row.appendChild(meta);

    bars.appendChild(row);
  });
  dom.insightsPanel.appendChild(bars);
}

function makeHistoryItem(entry) {
  const item = document.createElement("li");
  item.className = "history-item";

  const title = document.createElement("strong");
  title.textContent = entry.mode === MODES.batch ? entry.fileName || `Lote (${entry.fileCount} arquivos)` : entry.fileName;
  item.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "history-meta";
  meta.textContent = `${entry.at} • ${entry.totalDetections} detecções • ${entry.inferenceMs} ms`;
  item.appendChild(meta);

  const tagsWrap = document.createElement("div");
  tagsWrap.className = "history-tags";
  safeArray(entry.tags).slice(0, 8).forEach((tag) => {
    const chip = document.createElement("span");
    chip.textContent = tag;
    tagsWrap.appendChild(chip);
  });

  if (!tagsWrap.childElementCount) {
    const empty = document.createElement("p");
    empty.className = "history-meta";
    empty.textContent = "Sem tags";
    item.appendChild(empty);
  } else {
    item.appendChild(tagsWrap);
  }

  return item;
}

function renderHistory(entries) {
  clearElement(dom.historyList);

  if (!entries.length) {
    const li = document.createElement("li");
    li.className = "history-item";
    li.textContent = "Nenhum histórico registrado.";
    dom.historyList.appendChild(li);
    return;
  }

  const fragment = document.createDocumentFragment();
  entries.forEach((entry) => fragment.appendChild(makeHistoryItem(entry)));
  dom.historyList.appendChild(fragment);
}

function renderCustomPresets(presets) {
  clearElement(dom.customPresetList);
  if (!presets || !presets.length) {
    const item = document.createElement("li");
    item.className = "custom-preset-item custom-preset-empty";
    item.textContent = "Nenhum preset personalizado salvo.";
    dom.customPresetList.appendChild(item);
    return;
  }

  const fragment = document.createDocumentFragment();
  safeArray(presets).forEach((preset) => {
    const item = document.createElement("li");
    item.className = "custom-preset-item";

    const details = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = preset.name || "Preset";
    const subtitle = document.createElement("span");
    subtitle.textContent = `conf ${preset.config?.conf ?? "-"} • tags ${preset.config?.maxTags ?? "-"}`;
    details.appendChild(title);
    details.appendChild(subtitle);

    const applyButton = document.createElement("button");
    applyButton.type = "button";
    applyButton.className = "btn-mini";
    applyButton.dataset.action = "apply-preset";
    applyButton.dataset.presetId = String(preset.id || "");
    applyButton.textContent = "Aplicar";

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "btn-mini is-danger";
    deleteButton.dataset.action = "remove-preset";
    deleteButton.dataset.presetId = String(preset.id || "");
    deleteButton.textContent = "Excluir";

    item.appendChild(details);
    item.appendChild(applyButton);
    item.appendChild(deleteButton);
    fragment.appendChild(item);
  });

  dom.customPresetList.appendChild(fragment);
}

function renderJourneySteps(state) {
  if (!dom.journeySteps) {
    return;
  }

  const mapping = {
    input: Boolean(state?.inputReady),
    config: Boolean(state?.configReady),
    result: Boolean(state?.resultReady),
  };

  const children = Array.from(dom.journeySteps.querySelectorAll("li[data-step]"));
  children.forEach((item) => {
    const key = item.dataset.step;
    item.classList.remove("is-active", "is-done");
    if (!key || !Object.hasOwn(mapping, key)) {
      return;
    }

    if (key === "result" && mapping[key]) {
      item.classList.add("is-done");
      return;
    }

    if (mapping[key]) {
      item.classList.add("is-done");
      return;
    }

    if (key === "input") {
      item.classList.add("is-active");
      return;
    }

    if (key === "config" && mapping.input) {
      item.classList.add("is-active");
      return;
    }

    if (key === "result" && mapping.input && mapping.config) {
      item.classList.add("is-active");
    }
  });
}

function renderContextSummary(items) {
  if (!dom.contextSummary) {
    return;
  }

  clearElement(dom.contextSummary);
  const safeItems = safeArray(items);
  if (!safeItems.length) {
    const chip = document.createElement("span");
    chip.className = "context-chip";
    chip.textContent = "Sem contexto ativo";
    dom.contextSummary.appendChild(chip);
    return;
  }

  const fragment = document.createDocumentFragment();
  safeItems.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "context-chip";
    chip.textContent = String(item);
    fragment.appendChild(chip);
  });
  dom.contextSummary.appendChild(fragment);
}

function renderPreflight(items, isReady) {
  if (!dom.preflightList || !dom.preflightBadge) {
    return;
  }

  clearElement(dom.preflightList);
  dom.preflightBadge.classList.remove("is-success", "is-warning", "is-error");
  dom.preflightBadge.classList.add(isReady ? "is-success" : "is-warning");
  dom.preflightBadge.textContent = isReady ? "Pronto" : "Pendências";

  const safeItems = safeArray(items);
  if (!safeItems.length) {
    const li = document.createElement("li");
    li.className = "preflight-item";
    li.textContent = "Nenhum item para validar.";
    dom.preflightList.appendChild(li);
    return;
  }

  const fragment = document.createDocumentFragment();
  safeItems.forEach((item) => {
    const li = document.createElement("li");
    li.className = `preflight-item ${item.ok ? "is-ok" : "is-warning"}`;

    const title = document.createElement("strong");
    title.textContent = item.ok ? "OK" : "Revisar";

    const description = document.createElement("span");
    description.textContent = String(item.message || "");

    li.appendChild(title);
    li.appendChild(description);
    fragment.appendChild(li);
  });

  dom.preflightList.appendChild(fragment);
}

function setMode(mode) {
  const isSingle = mode === MODES.single;
  document.body.dataset.mode = isSingle ? "single" : "batch";

  dom.modeSingleBtn.classList.toggle("is-active", isSingle);
  dom.modeBatchBtn.classList.toggle("is-active", !isSingle);
  dom.modeSingleBtn.setAttribute("aria-pressed", String(isSingle));
  dom.modeBatchBtn.setAttribute("aria-pressed", String(!isSingle));

  dom.fileInput.multiple = !isSingle;
  dom.dropzoneTitle.textContent = isSingle ? "Arraste e solte uma imagem" : "Arraste e solte múltiplas imagens";
  dom.fileHint.textContent = isSingle
    ? "ou clique para selecionar um arquivo."
    : "ou clique para selecionar vários arquivos.";
  dom.modeHint.textContent = isSingle ? "Modo atual: imagem única." : "Modo atual: lote de imagens.";
}

function setBatchInputType(sourceType) {
  const isFiles = sourceType !== "urls";
  document.body.dataset.batchSource = isFiles ? "files" : "urls";
  dom.batchSourceFilesBtn.classList.toggle("is-active", isFiles);
  dom.batchSourceUrlsBtn.classList.toggle("is-active", !isFiles);
  dom.batchSourceFilesBtn.setAttribute("aria-pressed", String(isFiles));
  dom.batchSourceUrlsBtn.setAttribute("aria-pressed", String(!isFiles));
  dom.batchSourceHint.textContent = isFiles ? "Fonte atual: arquivos." : "Fonte atual: URLs.";
}

function setFormValues(config) {
  dom.confRange.value = String(config.conf);
  dom.confValue.textContent = Number(config.conf).toFixed(2);

  dom.maxTags.value = String(config.maxTags);
  dom.minArea.value = String(config.minAreaPercent);
  dom.includePerson.checked = Boolean(config.includePerson);

  dom.filterRange.value = String(config.visualFilterPercent);
  dom.filterValue.textContent = `${config.visualFilterPercent}%`;
  dom.includeLabels.value = config.includeLabels || "";
  dom.excludeLabels.value = config.excludeLabels || "";
  dom.apiKeyInput.value = config.apiKey || "";
}

function setUiSettings(settings) {
  const compact = Boolean(settings?.compactMode);
  const highContrast = Boolean(settings?.highContrastMode);

  document.documentElement.dataset.density = compact ? "compact" : "comfortable";
  document.documentElement.dataset.contrast = highContrast ? "high" : "normal";

  if (dom.compactMode) {
    dom.compactMode.checked = compact;
  }
  if (dom.highContrastMode) {
    dom.highContrastMode.checked = highContrast;
  }
  if (dom.toggleContrastBtn) {
    dom.toggleContrastBtn.textContent = highContrast ? "Contraste: Alto" : "Contraste";
  }
}

function setMetrics(metrics) {
  setText(dom.metricFiles, String(metrics.files || 0));
  setText(dom.metricDetections, String(metrics.detections || 0));
  setText(dom.metricInference, `${metrics.inference || 0} ms`);
  setText(dom.metricUnique, String(metrics.uniqueTags || 0));
}

function setStatus(message, variant = STATUS_VARIANT.neutral) {
  setText(dom.statusMessage, message);
  setStatusVariant(variant);
}

function setLoading(isLoading) {
  dom.analyzeBtn.disabled = isLoading;
  const baseLabel = dom.analyzeBtn.dataset.baseLabel || "Analisar";
  if (isLoading) {
    dom.analyzeBtn.textContent = "Processando...";
    return;
  }
  dom.analyzeBtn.textContent = baseLabel;
}

function setActionAvailability({ canExport, canCopy }) {
  dom.downloadBtn.disabled = !canExport;
  dom.copyTagsBtn.disabled = !canCopy;
}

function renderOpsFieldPanel(panel, fields, emptyMessage) {
  clearElement(panel);
  if (!fields || !fields.length) {
    panel.className = "ops-panel-empty";
    panel.textContent = emptyMessage;
    return;
  }

  panel.className = "ops-panel-grid";
  const fragment = document.createDocumentFragment();
  fields.forEach(([label, value]) => {
    const item = document.createElement("article");
    item.className = "ops-item";

    const name = document.createElement("span");
    name.textContent = String(label);
    const amount = document.createElement("strong");
    amount.textContent = value === undefined || value === null ? "-" : String(value);

    item.appendChild(name);
    item.appendChild(amount);
    fragment.appendChild(item);
  });
  panel.appendChild(fragment);
}

function renderRecentPanel(recentSummary, recentItems) {
  clearElement(dom.recentPanel);

  if (!recentSummary && (!recentItems || !recentItems.length)) {
    dom.recentPanel.className = "ops-panel-empty";
    dom.recentPanel.textContent = "Sem dados recentes.";
    return;
  }

  dom.recentPanel.className = "recent-panel-list";

  const summary = document.createElement("article");
  summary.className = "recent-item";

  const summaryTitle = document.createElement("strong");
  summaryTitle.textContent = "Resumo da janela recente";
  summary.appendChild(summaryTitle);

  const summaryMeta = document.createElement("p");
  summaryMeta.className = "recent-meta";
  const hitRatioPercent = Number(recentSummary?.cache_hit_ratio || 0) * 100;
  summaryMeta.textContent = `${recentSummary?.window_size || 0} análises • cache hit ${hitRatioPercent.toFixed(1)}%`;
  summary.appendChild(summaryMeta);

  const sourceWrap = document.createElement("div");
  sourceWrap.className = "recent-tags";
  const sources = recentSummary?.sources || {};
  if (Object.keys(sources).length === 0) {
    const emptySource = document.createElement("span");
    emptySource.textContent = "Sem fontes";
    sourceWrap.appendChild(emptySource);
  } else {
    Object.entries(sources).forEach(([source, count]) => {
      const chip = document.createElement("span");
      chip.textContent = `${source}: ${count}`;
      sourceWrap.appendChild(chip);
    });
  }
  summary.appendChild(sourceWrap);
  dom.recentPanel.appendChild(summary);

  safeArray(recentItems)
    .slice(0, 6)
    .forEach((entry) => {
      const item = document.createElement("article");
      item.className = "recent-item";

      const title = document.createElement("strong");
      title.textContent = `${entry.source} • ${entry.total_detections} detecções`;
      item.appendChild(title);

      const meta = document.createElement("p");
      meta.className = "recent-meta";
      meta.textContent = `${entry.timestamp} • ${entry.inference_ms} ms • principal ${entry.principal_id}`;
      item.appendChild(meta);

      const tags = document.createElement("div");
      tags.className = "recent-tags";
      safeArray(entry.tags)
        .slice(0, 6)
        .forEach((tag) => {
          const chip = document.createElement("span");
          chip.textContent = tag;
          tags.appendChild(chip);
        });
      item.appendChild(tags);
      dom.recentPanel.appendChild(item);
    });
}

function renderOperationalOverview(overview) {
  if (!overview) {
    renderOpsFieldPanel(dom.metricsPanel, null, "Painel ainda não carregado.");
    renderOpsFieldPanel(dom.runtimePanel, null, "Sem dados de runtime.");
    renderRecentPanel(null, []);
    return;
  }

  const metrics = overview.metrics || {};
  const recent = overview.recent || {};
  const topTags = recent.top_tags || {};
  const statusClasses = metrics.requests_by_status_class || {};
  const statusText = Object.keys(statusClasses).length
    ? Object.entries(statusClasses)
        .map(([status, count]) => `${status}:${count}`)
        .join(" • ")
    : "sem dados";
  const topTagsText = Object.keys(topTags).length
    ? Object.entries(topTags)
        .map(([tag, count]) => `${tag} (${count})`)
        .join(", ")
    : "Sem tags recentes";

  renderOpsFieldPanel(
    dom.metricsPanel,
    [
      ["Requests", metrics.requests_total],
      ["Erros", metrics.errors_total],
      ["Detecções", metrics.detections_total],
      ["Cache hits", metrics.cache_hits],
      ["Cache itens", overview.cache_items],
      ["Latência média", `${metrics.average_latency_ms} ms`],
      ["Latência p95", `${metrics.p95_latency_ms} ms`],
      ["Latência p99", `${metrics.p99_latency_ms} ms`],
      ["Uptime", `${metrics.uptime_seconds}s`],
      ["Status", statusText],
      ["Top tags", topTagsText],
    ],
    "Painel ainda não carregado."
  );

  const runtime = overview.runtime || {};
  renderOpsFieldPanel(
    dom.runtimePanel,
    [
      ["Versão", runtime.app_version],
      ["Auth", runtime.auth_required ? "Obrigatória" : "Opcional"],
      ["Rate limit", `${runtime.rate_limit_per_minute}/min`],
      ["Upload máx", `${runtime.max_upload_mb} MB`],
      ["Batch máx", runtime.max_batch_files],
      ["Concorrência", runtime.max_concurrent_inference],
      ["Fetch remoto", runtime.max_concurrent_remote_fetch],
      ["Timeout inferência", `${runtime.inference_timeout_seconds}s`],
      ["TTL cache", `${runtime.cache_ttl_seconds}s`],
      ["GZip", runtime.enable_gzip ? "Ativo" : "Inativo"],
    ],
    "Sem dados de runtime."
  );

  renderRecentPanel(recent, overview.recent_items);
}

function focusHistorySearch() {
  dom.historySearch.focus();
}

function openShortcuts() {
  if (dom.shortcutsDialog && typeof dom.shortcutsDialog.showModal === "function") {
    dom.shortcutsDialog.showModal();
  }
}

function closeShortcuts() {
  if (dom.shortcutsDialog && typeof dom.shortcutsDialog.close === "function" && dom.shortcutsDialog.open) {
    dom.shortcutsDialog.close();
  }
}

export const ui = {
  dom,
  setMode,
  setBatchInputType,
  setFormValues,
  setUiSettings,
  setStatus,
  setLoading,
  setActionAvailability,
  setMetrics,
  renderSinglePreview,
  renderFileQueue,
  renderUrlQueue,
  renderTags,
  renderTagDelta,
  renderDetections,
  renderBatchResults,
  renderHistory,
  renderCustomPresets,
  renderJourneySteps,
  renderContextSummary,
  renderPreflight,
  renderInsights,
  focusHistorySearch,
  openShortcuts,
  closeShortcuts,
  renderOperationalOverview,
};
