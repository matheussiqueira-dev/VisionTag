import { API_ROUTES } from "./constants.js";

function parseResponseError(payload) {
  if (!payload) {
    return "Erro inesperado na comunicação com a API.";
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    return payload.detail
      .map((item) => item.msg || item.type || "erro de validação")
      .join("; ");
  }

  return "Falha ao processar a requisição.";
}

function buildQueryParams(config) {
  const params = new URLSearchParams();
  params.set("conf", String(config.conf));
  params.set("max_tags", String(config.maxTags));
  params.set("min_area", String(config.minAreaPercent / 100));
  params.set("include_person", String(config.includePerson));
  if (config.includeLabels && String(config.includeLabels).trim()) {
    params.set("include_labels", String(config.includeLabels).trim());
  }
  if (config.excludeLabels && String(config.excludeLabels).trim()) {
    params.set("exclude_labels", String(config.excludeLabels).trim());
  }
  return params.toString();
}

function buildAuthHeaders(config) {
  const headers = {};
  const apiKey = String(config?.apiKey || "").trim();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

async function parseJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function detectSingle(file, config, signal) {
  const queryString = buildQueryParams(config);
  const body = new FormData();
  body.append("file", file);
  const headers = buildAuthHeaders(config);

  const response = await fetch(`${API_ROUTES.detectSingle}?${queryString}`, {
    method: "POST",
    body,
    headers,
    signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(parseResponseError(payload));
  }

  return payload;
}

export async function detectBatch(files, config, signal) {
  const queryString = buildQueryParams(config);
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  const headers = buildAuthHeaders(config);

  const response = await fetch(`${API_ROUTES.detectBatch}?${queryString}`, {
    method: "POST",
    body,
    headers,
    signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(parseResponseError(payload));
  }

  return payload;
}

export async function detectByUrl(imageUrl, config, signal) {
  const queryString = buildQueryParams(config);
  const headers = {
    ...buildAuthHeaders(config),
    "Content-Type": "application/json",
  };

  const response = await fetch(`${API_ROUTES.detectUrl}?${queryString}`, {
    method: "POST",
    headers,
    body: JSON.stringify({ image_url: imageUrl }),
    signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(parseResponseError(payload));
  }

  return payload;
}

export async function fetchOperationalMetrics(config, signal) {
  const headers = buildAuthHeaders(config);
  const response = await fetch(API_ROUTES.metrics, {
    method: "GET",
    headers,
    signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(parseResponseError(payload));
  }
  return payload;
}
