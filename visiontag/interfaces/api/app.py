from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ... import __version__
from ...core.exceptions import InputValidationError, ModelInferenceError
from ...core.models import DetectionRequest
from ...core.settings import AppSettings
from ...infrastructure.image_io import decode_image_bytes
from ...infrastructure.yolo_detector import YoloObjectDetector
from ...labels_pt import COCO_PT
from ...services.tagging import TaggingService
from .schemas import (
    ApiConfigResponse,
    BatchDetectItem,
    BatchDetectMeta,
    BatchDetectResponse,
    DetectMeta,
    DetectionItem,
    DetectResponse,
    ErrorResponse,
)


LOGGER = logging.getLogger("visiontag.api")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _build_default_service(settings: AppSettings) -> TaggingService:
    return TaggingService(
        detector=YoloObjectDetector(model_path=settings.model_path),
        label_map=COCO_PT,
    )


def _resolve_detection_request(
    settings: AppSettings,
    conf: float | None,
    max_tags: int | None,
    min_area: float | None,
    include_person: bool | None,
) -> DetectionRequest:
    return DetectionRequest(
        conf_threshold=settings.default_conf if conf is None else conf,
        max_tags=settings.default_max_tags if max_tags is None else max_tags,
        min_area_ratio=settings.default_min_area_ratio if min_area is None else min_area,
        include_person=(
            settings.default_include_person if include_person is None else include_person
        ),
    )


def create_app(
    settings: AppSettings | None = None,
    service: TaggingService | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_service = service or _build_default_service(resolved_settings)

    app = FastAPI(
        title="VisionTag",
        version=__version__,
        description=(
            "API de visao computacional para deteccao de objetos e geracao de tags "
            "em portugues."
        ),
    )
    app.state.settings = resolved_settings
    app.state.service = resolved_service

    if resolved_settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_allow_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def observe_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                "request_id=%s method=%s path=%s erro_interno=1",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-Id"] = request_id
        LOGGER.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(InputValidationError)
    async def input_validation_exception_handler(_: Request, exc: InputValidationError):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    @app.exception_handler(ModelInferenceError)
    async def model_exception_handler(_: Request, exc: ModelInferenceError):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    def get_settings(request: Request) -> AppSettings:
        return request.app.state.settings

    def get_service(request: Request) -> TaggingService:
        return request.app.state.service

    def require_api_key(
        request: Request,
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        current_settings: AppSettings = request.app.state.settings
        if current_settings.api_key and x_api_key != current_settings.api_key:
            raise HTTPException(status_code=401, detail="Chave de API invalida.")

    @app.get("/health")
    async def health(settings_dep: AppSettings = Depends(get_settings)):
        return {
            "status": "ok",
            "service": "visiontag",
            "version": __version__,
            "model": settings_dep.model_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/v1/config", response_model=ApiConfigResponse)
    async def api_config(settings_dep: AppSettings = Depends(get_settings)):
        return ApiConfigResponse(
            api_key_required=bool(settings_dep.api_key),
            defaults={
                "conf": settings_dep.default_conf,
                "max_tags": settings_dep.default_max_tags,
                "min_area": settings_dep.default_min_area_ratio,
                "include_person": settings_dep.default_include_person,
            },
            limits={
                "max_upload_bytes": settings_dep.max_upload_bytes,
                "max_batch_files": settings_dep.max_batch_files,
            },
        )

    @app.post(
        "/api/v1/detect",
        response_model=DetectResponse,
        responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def detect(
        file: UploadFile = File(...),
        include_details: Annotated[bool, Query(description="Retorna bbox e confianca")] = False,
        conf: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
        max_tags: Annotated[int | None, Query(ge=1, le=50)] = None,
        min_area: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
        include_person: bool | None = None,
        settings_dep: AppSettings = Depends(get_settings),
        service_dep: TaggingService = Depends(get_service),
        _: None = Depends(require_api_key),
    ):
        started = time.perf_counter()
        payload = await file.read()
        image = decode_image_bytes(
            data=payload,
            content_type=file.content_type,
            max_upload_bytes=settings_dep.max_upload_bytes,
        )
        request_data = _resolve_detection_request(
            settings=settings_dep,
            conf=conf,
            max_tags=max_tags,
            min_area=min_area,
            include_person=include_person,
        )
        result = service_dep.analyze(image, request_data)
        elapsed_ms = (time.perf_counter() - started) * 1000
        detections_payload = (
            [
                DetectionItem(label=item.label, confidence=item.confidence, bbox=item.bbox)
                for item in result.detections
            ]
            if include_details
            else None
        )
        return DetectResponse(
            tags=result.tags,
            detections=detections_payload,
            meta=DetectMeta(
                width=result.image_width,
                height=result.image_height,
                model=settings_dep.model_path,
                latency_ms=elapsed_ms,
            ),
        )

    @app.post("/detect", include_in_schema=False)
    async def detect_legacy(
        file: UploadFile = File(...),
        settings_dep: AppSettings = Depends(get_settings),
        service_dep: TaggingService = Depends(get_service),
        _: None = Depends(require_api_key),
    ):
        payload = await file.read()
        image = decode_image_bytes(
            data=payload,
            content_type=file.content_type,
            max_upload_bytes=settings_dep.max_upload_bytes,
        )
        request_data = _resolve_detection_request(
            settings=settings_dep,
            conf=None,
            max_tags=None,
            min_area=None,
            include_person=None,
        )
        result = service_dep.analyze(image, request_data)
        return {"tags": result.tags}

    @app.post(
        "/api/v1/detect/batch",
        response_model=BatchDetectResponse,
        responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def detect_batch(
        files: list[UploadFile] = File(...),
        include_details: Annotated[bool, Query(description="Retorna bbox e confianca")] = False,
        conf: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
        max_tags: Annotated[int | None, Query(ge=1, le=50)] = None,
        min_area: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
        include_person: bool | None = None,
        settings_dep: AppSettings = Depends(get_settings),
        service_dep: TaggingService = Depends(get_service),
        _: None = Depends(require_api_key),
    ):
        if not files:
            raise InputValidationError("Nenhum arquivo enviado.")
        if len(files) > settings_dep.max_batch_files:
            raise InputValidationError(
                f"Lote excede limite de {settings_dep.max_batch_files} arquivos."
            )

        started = time.perf_counter()
        request_data = _resolve_detection_request(
            settings=settings_dep,
            conf=conf,
            max_tags=max_tags,
            min_area=min_area,
            include_person=include_person,
        )
        failed = 0
        items: list[BatchDetectItem] = []

        for file in files:
            file_name = file.filename or "arquivo_sem_nome"
            try:
                payload = await file.read()
                image = decode_image_bytes(
                    data=payload,
                    content_type=file.content_type,
                    max_upload_bytes=settings_dep.max_upload_bytes,
                )
                result = service_dep.analyze(image, request_data)
                detections_payload = (
                    [
                        DetectionItem(label=item.label, confidence=item.confidence, bbox=item.bbox)
                        for item in result.detections
                    ]
                    if include_details
                    else None
                )
                items.append(
                    BatchDetectItem(
                        filename=file_name,
                        tags=result.tags,
                        detections=detections_payload,
                    )
                )
            except InputValidationError as exc:
                failed += 1
                items.append(BatchDetectItem(filename=file_name, tags=[], error=str(exc)))
            except Exception as exc:
                failed += 1
                LOGGER.exception("Erro inesperado no processamento de lote: %s", file_name)
                items.append(
                    BatchDetectItem(
                        filename=file_name,
                        tags=[],
                        error=f"Falha interna no processamento ({exc.__class__.__name__}).",
                    )
                )

        elapsed_ms = (time.perf_counter() - started) * 1000
        return BatchDetectResponse(
            items=items,
            meta=BatchDetectMeta(
                processed=len(files),
                failed=failed,
                model=settings_dep.model_path,
                latency_ms=elapsed_ms,
            ),
        )

    static_dir = Path(__file__).resolve().parents[1] / "web" / "static"
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def web_ui():
        return FileResponse(static_dir / "index.html")

    return app
