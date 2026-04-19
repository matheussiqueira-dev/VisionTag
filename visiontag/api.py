from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from .config import VisionTagConfig
from .detector import VisionTagger

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
_START_TIME = time.time()

_config = VisionTagConfig()
_tagger: VisionTagger | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tagger
    logger.info("Inicializando VisionTagger...")
    _tagger = VisionTagger(config=_config)
    logger.info("VisionTagger pronto.")
    yield
    logger.info("Encerrando VisionTag API.")


app = FastAPI(
    title="VisionTag",
    description="API de deteccao de objetos em imagens com tags em portugues.",
    version="1.0.0",
    lifespan=lifespan,
)


def _get_tagger() -> VisionTagger:
    if _tagger is None:
        raise HTTPException(status_code=503, detail="Modelo ainda nao carregado")
    return _tagger


@app.get("/health", summary="Verificacao de saude")
async def health():
    return {"status": "ok", "uptime_seconds": round(time.time() - _START_TIME, 1)}


@app.get("/info", summary="Informacoes do modelo")
async def info():
    return {
        "model": _config.model_path,
        "conf_threshold": _config.conf,
        "max_tags": _config.max_tags,
        "min_area_ratio": _config.min_area_ratio,
        "include_person": _config.include_person,
    }


@app.post("/detect", summary="Detectar objetos em uma imagem")
async def detect(file: UploadFile = File(..., description="Imagem JPG, PNG ou WebP")):
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Tipo de arquivo nao suportado. Use JPEG, PNG, WebP ou BMP.",
        )

    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if len(data) > _config.api_max_upload_bytes:
        limit_mb = _config.api_max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Arquivo muito grande. Limite: {limit_mb} MB")

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="Nao foi possivel decodificar a imagem")

    tagger = _get_tagger()
    try:
        detections = tagger.detect_with_scores(image)
    except (ValueError, RuntimeError) as exc:
        logger.exception("Erro na deteccao")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    tags = [d["tag"] for d in detections]
    return {"tags": tags, "detections": detections}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Excecao nao tratada em %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})
