import { clamp, safeArray } from "./helpers.js";

function normalizeCsvLabels(rawValue) {
  return String(rawValue || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

export function hasConfigConflict(config) {
  const include = new Set(normalizeCsvLabels(config?.includeLabels));
  const exclude = new Set(normalizeCsvLabels(config?.excludeLabels));
  for (const label of include) {
    if (exclude.has(label)) {
      return true;
    }
  }
  return false;
}

export function parseBatchUrls(rawValue, maxItems = 12) {
  if (!rawValue) {
    return [];
  }

  const parts = String(rawValue)
    .split(/\r?\n|,/g)
    .map((item) => item.trim())
    .filter(Boolean);
  return Array.from(new Set(parts)).slice(0, Math.max(1, maxItems));
}

export function deriveJourneyState({
  mode,
  batchSource,
  selectedFile,
  imageUrl,
  batchFiles,
  batchUrls,
  configConflict,
  hasResult,
}) {
  const inputReady =
    mode === "single"
      ? Boolean(selectedFile || String(imageUrl || "").trim())
      : batchSource === "urls"
        ? safeArray(batchUrls).length > 0
        : safeArray(batchFiles).length > 0;

  return {
    inputReady,
    configReady: !configConflict,
    resultReady: Boolean(hasResult),
  };
}

export function buildContextItems({
  mode,
  batchSource,
  selectedFile,
  imageUrl,
  batchFiles,
  batchUrls,
  config,
}) {
  const entriesCount =
    mode === "single"
      ? selectedFile || String(imageUrl || "").trim()
        ? 1
        : 0
      : batchSource === "urls"
        ? safeArray(batchUrls).length
        : safeArray(batchFiles).length;

  return [
    mode === "single" ? "Modo: Único" : "Modo: Lote",
    mode === "single" ? "Fonte: Upload/URL" : batchSource === "urls" ? "Fonte lote: URLs" : "Fonte lote: Arquivos",
    `${entriesCount} entrada(s)`,
    `Conf ${Number(config?.conf ?? 0).toFixed(2)}`,
    `Max tags ${Number(config?.maxTags ?? 0)}`,
    `Filtro visual ${Number(config?.visualFilterPercent ?? 0)}%`,
  ];
}

export function buildPreflightItems({ journey, configConflict, batchSize, hasApiKey }) {
  return [
    {
      ok: Boolean(journey.inputReady),
      message: journey.inputReady
        ? "Entrada válida detectada para o modo atual."
        : "Adicione uma imagem ou URL antes de executar a análise.",
    },
    {
      ok: !configConflict,
      message: configConflict
        ? "Conflito de labels: a mesma label está em incluir e excluir."
        : "Parâmetros de inferência consistentes.",
    },
    {
      ok: batchSize <= 10,
      message:
        batchSize > 10
          ? "Lote grande: considere reduzir volume para resposta mais previsível."
          : "Volume de lote adequado para execução responsiva.",
    },
    {
      ok: true,
      message: hasApiKey
        ? "Autenticação ativa por API key."
        : "API key opcional (necessária apenas em ambientes protegidos).",
    },
  ];
}

function collectDetections(mode, singleResult, batchResult) {
  if (mode === "single") {
    return safeArray(singleResult?.detections);
  }

  return safeArray(batchResult?.items).flatMap((item) => safeArray(item?.result?.detections));
}

export function buildRecommendations({
  mode,
  batchSource,
  config,
  journey,
  preflightItems,
  singleResult,
  batchResult,
  batchSize,
}) {
  let score = 100;
  const items = [];
  const detections = collectDetections(mode, singleResult, batchResult);
  const avgConfidence = detections.length
    ? detections.reduce((sum, item) => sum + (Number(item?.confidence) || 0), 0) / detections.length
    : 0;
  const totalDetections =
    mode === "single"
      ? Number(singleResult?.total_detections || 0)
      : safeArray(batchResult?.items).reduce((sum, item) => sum + Number(item?.result?.total_detections || 0), 0);

  const hasPendingPreflight = preflightItems.some((item) => !item.ok);
  if (hasPendingPreflight) {
    score -= 20;
    items.push({
      tone: "warning",
      title: "Resolva pendências antes de analisar",
      description: "Complete os itens de pré-execução para evitar falhas e retrabalho.",
    });
  }

  if (!journey.resultReady && Number(config?.conf) >= 0.82) {
    score -= 10;
    items.push({
      tone: "info",
      title: "Confiança alta pode reduzir cobertura",
      description: "Se houver poucos resultados, teste confiança entre 0.60 e 0.75.",
    });
  }

  if (journey.resultReady && avgConfidence > 0 && avgConfidence < 0.55) {
    score -= 8;
    items.push({
      tone: "warning",
      title: "Detecções com baixa confiança média",
      description: "Ajuste área mínima e filtros de labels para reduzir ruído.",
    });
  }

  if (journey.resultReady && totalDetections >= 12 && Number(config?.maxTags) <= 5) {
    score -= 7;
    items.push({
      tone: "info",
      title: "Volume alto de objetos detectados",
      description: "Considere elevar `max tags` para melhorar visibilidade do cenário.",
    });
  }

  if (mode === "batch" && batchSource === "urls" && batchSize > 0) {
    items.push({
      tone: "success",
      title: "Fluxo remoto otimizado",
      description: "Lote por URLs reduz fricção operacional em integrações distribuídas.",
    });
  }

  if (journey.resultReady && items.length <= 1) {
    items.push({
      tone: "success",
      title: "Configuração saudável",
      description: "Seu fluxo está estável e pronto para escalar o volume de análises.",
    });
  }

  score = clamp(score, 0, 100);
  const level = score >= 85 ? "excellent" : score >= 65 ? "good" : "attention";
  return { score, level, items: items.slice(0, 4) };
}
