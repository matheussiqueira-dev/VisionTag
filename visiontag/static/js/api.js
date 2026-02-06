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
  return params.toString();
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

  const response = await fetch(`${API_ROUTES.detectSingle}?${queryString}`, {
    method: "POST",
    body,
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

  const response = await fetch(`${API_ROUTES.detectBatch}?${queryString}`, {
    method: "POST",
    body,
    signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(parseResponseError(payload));
  }

  return payload;
}
