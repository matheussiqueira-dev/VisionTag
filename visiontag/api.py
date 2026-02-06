from __future__ import annotations

import os
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .detector import DetectionOptions, VisionTagger
from .labels_pt import COCO_PT
from .schemas import BatchDetectResponse, BatchItemResult, BoundingBox, DetectionItem, DetectionResult, HealthResponse
from .utils import decode_image, is_allowed_content_type, tag_frequency

MODEL_PATH = os.getenv("VISIONTAG_MODEL_PATH", "yolov8n.pt")
MAX_UPLOAD_MB = int(os.getenv("VISIONTAG_MAX_UPLOAD_MB", "8"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_DIMENSION = int(os.getenv("VISIONTAG_MAX_DIMENSION", "1280"))
MAX_BATCH_FILES = int(os.getenv("VISIONTAG_MAX_BATCH_FILES", "10"))

app = FastAPI(
    title="VisionTag API",
    version="2.0.0",
    description="Deteccao de objetos com tags em portugues, resultados detalhados e processamento em lote.",
)

tagger = VisionTagger(model_path=MODEL_PATH, max_dimension=MAX_IMAGE_DIMENSION)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "VisionTag API em execucao.",
        "docs": "/docs",
    }


def detection_options_dependency(
    conf: float = Query(default=0.7, ge=0.01, le=1.0),
    max_tags: int = Query(default=5, ge=1, le=25),
    min_area: float = Query(default=0.01, ge=0.0, le=1.0),
    include_person: bool = Query(default=False),
) -> DetectionOptions:
    return DetectionOptions(
        conf=conf,
        max_tags=max_tags,
        min_area_ratio=min_area,
        include_person=include_person,
    )


async def read_valid_upload(file: UploadFile) -> bytes:
    if not is_allowed_content_type(file.content_type):
        raise HTTPException(status_code=415, detail="Formato de imagem nao suportado.")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo maior que {MAX_UPLOAD_MB} MB.",
        )
    return data


def build_detection_result(image, options: DetectionOptions) -> DetectionResult:
    summary = tagger.detect_detailed(image, options)
    detections = [
        DetectionItem(
            label=item.label,
            confidence=round(item.confidence, 4),
            bbox=BoundingBox(
                x1=round(item.bbox[0], 2),
                y1=round(item.bbox[1], 2),
                x2=round(item.bbox[2], 2),
                y2=round(item.bbox[3], 2),
            ),
        )
        for item in summary.detections
    ]

    return DetectionResult(
        tags=summary.tags,
        detections=detections,
        total_detections=len(detections),
        inference_ms=round(summary.inference_ms, 2),
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_path=tagger.model_path,
        labels_count=len(COCO_PT),
    )


@app.get("/api/v1/labels")
def labels() -> dict:
    return {
        "total": len(COCO_PT),
        "labels": sorted(set(COCO_PT.values())),
    }


@app.post("/api/v1/detect", response_model=DetectionResult)
async def detect(
    file: UploadFile = File(...),
    options: DetectionOptions = Depends(detection_options_dependency),
) -> DetectionResult:
    data = await read_valid_upload(file)
    image = decode_image(data)
    if image is None:
        raise HTTPException(status_code=400, detail="Imagem invalida ou corrompida.")
    return build_detection_result(image, options)


@app.post("/api/v1/detect/batch", response_model=BatchDetectResponse)
async def detect_batch(
    files: List[UploadFile] = File(...),
    options: DetectionOptions = Depends(detection_options_dependency),
) -> BatchDetectResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Quantidade maxima de arquivos por lote: {MAX_BATCH_FILES}.",
        )

    items: List[BatchItemResult] = []
    all_tags: List[str] = []

    for file in files:
        filename = file.filename or "arquivo"
        try:
            data = await read_valid_upload(file)
            image = decode_image(data)
            if image is None:
                raise HTTPException(status_code=400, detail="Imagem invalida ou corrompida.")

            result = build_detection_result(image, options)
            items.append(BatchItemResult(filename=filename, result=result))
            all_tags.extend(result.tags)
        except HTTPException as exc:
            items.append(BatchItemResult(filename=filename, error=str(exc.detail)))

    return BatchDetectResponse(items=items, summary=tag_frequency(all_tags))


@app.post("/detect")
async def legacy_detect(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    image = decode_image(data)
    if image is None:
        raise HTTPException(status_code=400, detail="Imagem invalida.")

    tags = tagger.detect(image)
    return {"tags": tags}
