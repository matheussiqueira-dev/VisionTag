from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import List
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Query, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .detector import DetectionOptions
from .errors import AppError, InvalidInputError, PayloadTooLargeError, UnsupportedMediaTypeError, register_exception_handlers
from .logging_config import configure_logging
from .schemas import (
    BatchDetectResponse,
    BatchItemResult,
    BatchSummary,
    CacheClearResponse,
    CacheStatsResponse,
    DetectionResult,
    HealthResponse,
    LabelsResponse,
    RuntimeSettingsResponse,
    TelemetryResponse,
)
from .security import AuthService, SlidingWindowRateLimiter, require_access
from .services import DetectionServiceProvider
from .services.detection_service import build_detection_options, labels_catalog
from .telemetry import TelemetryStore
from .utils import is_allowed_content_type, sanitize_filename, tag_frequency

settings = Settings.from_env()
configure_logging(settings.log_level)
logger = logging.getLogger("visiontag.api")


def create_app(app_settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info(
            "VisionTag started | version=%s | auth_required=%s | rate_limit=%s/min",
            app_settings.app_version,
            app_settings.auth_required,
            app_settings.rate_limit_per_minute,
        )
        yield
        logger.info("VisionTag shutdown complete")

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="API de deteccao visual com contratos versionados, seguranca por escopo e telemetria operacional.",
        lifespan=lifespan,
    )

    telemetry = TelemetryStore()
    auth_service = AuthService(app_settings)
    rate_limiter = SlidingWindowRateLimiter(limit=app_settings.rate_limit_per_minute)

    detection_provider = DetectionServiceProvider(
        model_path=app_settings.model_path,
        max_dimension=app_settings.max_dimension,
        cache_max_items=app_settings.cache_max_items,
        cache_ttl_seconds=app_settings.cache_ttl_seconds,
        telemetry=telemetry,
    )

    app.state.settings = app_settings
    app.state.telemetry = telemetry
    app.state.auth_service = auth_service
    app.state.rate_limiter = rate_limiter
    app.state.detection_service_provider = detection_provider

    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self'; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none';",
    }

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = uuid4().hex
        request.state.request_id = request_id
        started = monotonic()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            latency_ms = (monotonic() - started) * 1000
            app.state.telemetry.record_request(path=request.url.path, status_code=status_code, latency_ms=latency_ms)
            raise

        response.headers["X-Request-ID"] = request_id
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value

        latency_ms = (monotonic() - started) * 1000
        app.state.telemetry.record_request(path=request.url.path, status_code=status_code, latency_ms=latency_ms)
        return response

    register_exception_handlers(app)

    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def detection_options_dependency(
        conf: float = Query(default=0.7, ge=0.01, le=1.0),
        max_tags: int = Query(default=5, ge=1, le=25),
        min_area: float = Query(default=0.01, ge=0.0, le=1.0),
        include_person: bool = Query(default=False),
        include_labels: str | None = Query(default=None, max_length=400),
        exclude_labels: str | None = Query(default=None, max_length=400),
    ) -> DetectionOptions:
        return build_detection_options(
            conf=conf,
            max_tags=max_tags,
            min_area=min_area,
            include_person=include_person,
            include_labels=include_labels,
            exclude_labels=exclude_labels,
        )

    async def read_valid_upload(file: UploadFile) -> bytes:
        if not is_allowed_content_type(file.content_type):
            raise UnsupportedMediaTypeError("Formato de imagem nao suportado.")

        data = await file.read(app_settings.max_upload_bytes + 1)
        if not data:
            raise InvalidInputError("Arquivo vazio.")
        if len(data) > app_settings.max_upload_bytes:
            raise PayloadTooLargeError(f"Arquivo maior que {app_settings.max_upload_mb} MB.")

        return data

    @app.get("/", include_in_schema=False)
    def index():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "VisionTag API em execucao.", "docs": "/docs"}

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=app_settings.app_version,
            model_path=app_settings.model_path,
            model_loaded=app.state.detection_service_provider.model_loaded,
            labels_count=len(labels_catalog()),
            auth_required=app_settings.auth_required,
            rate_limit_per_minute=app_settings.rate_limit_per_minute,
        )

    @app.get("/api/v1/labels", response_model=LabelsResponse)
    def labels() -> LabelsResponse:
        labels = labels_catalog()
        return LabelsResponse(total=len(labels), labels=labels)

    @app.get(
        "/api/v1/metrics",
        response_model=TelemetryResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def metrics() -> TelemetryResponse:
        snapshot = app.state.telemetry.snapshot()
        return TelemetryResponse(
            uptime_seconds=snapshot.uptime_seconds,
            requests_total=snapshot.requests_total,
            errors_total=snapshot.errors_total,
            detections_total=snapshot.detections_total,
            cache_hits=snapshot.cache_hits,
            average_latency_ms=snapshot.average_latency_ms,
            requests_by_path=snapshot.requests_by_path,
        )

    @app.get(
        "/api/v1/admin/runtime",
        response_model=RuntimeSettingsResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def runtime() -> RuntimeSettingsResponse:
        return RuntimeSettingsResponse(
            app_name=app_settings.app_name,
            app_version=app_settings.app_version,
            auth_required=app_settings.auth_required,
            rate_limit_per_minute=app_settings.rate_limit_per_minute,
            max_upload_mb=app_settings.max_upload_mb,
            max_batch_files=app_settings.max_batch_files,
            max_dimension=app_settings.max_dimension,
            cache_ttl_seconds=app_settings.cache_ttl_seconds,
            cache_max_items=app_settings.cache_max_items,
        )

    @app.get(
        "/api/v1/admin/cache",
        response_model=CacheStatsResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def cache_stats() -> CacheStatsResponse:
        return CacheStatsResponse(cache_items=app.state.detection_service_provider.cache_size())

    @app.delete(
        "/api/v1/admin/cache",
        response_model=CacheClearResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def cache_clear() -> CacheClearResponse:
        removed = app.state.detection_service_provider.clear_cache()
        return CacheClearResponse(removed_items=removed)

    @app.post(
        "/api/v1/detect",
        response_model=DetectionResult,
        dependencies=[Depends(require_access("detect", apply_rate_limit=True))],
    )
    async def detect(
        file: UploadFile = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ):
        data = await read_valid_upload(file)
        service = app.state.detection_service_provider.get()
        return service.detect_from_bytes(payload=data, options=options)

    @app.post(
        "/api/v1/detect/batch",
        response_model=BatchDetectResponse,
        dependencies=[Depends(require_access("detect", apply_rate_limit=True))],
    )
    async def detect_batch(
        files: List[UploadFile] = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> BatchDetectResponse:
        if not files:
            raise InvalidInputError("Nenhum arquivo enviado.")
        if len(files) > app_settings.max_batch_files:
            raise InvalidInputError(f"Quantidade maxima de arquivos por lote: {app_settings.max_batch_files}.")

        service = app.state.detection_service_provider.get()

        items: List[BatchItemResult] = []
        all_tags: List[str] = []
        success = 0
        failed = 0
        cached_hits = 0

        for upload in files:
            filename = sanitize_filename(upload.filename)
            try:
                payload = await read_valid_upload(upload)
                result = service.detect_from_bytes(payload=payload, options=options)
                items.append(BatchItemResult(filename=filename, result=result))
                all_tags.extend(result.tags)
                success += 1
                if result.cached:
                    cached_hits += 1
            except AppError as exc:
                items.append(BatchItemResult(filename=filename, error=exc.message))
                failed += 1

        summary = BatchSummary(
            total_files=len(files),
            success=success,
            failed=failed,
            cached_hits=cached_hits,
            top_tags=tag_frequency(all_tags),
        )
        return BatchDetectResponse(items=items, summary=summary)

    @app.post("/detect", dependencies=[Depends(require_access("detect", apply_rate_limit=True))])
    async def legacy_detect(
        file: UploadFile = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> dict:
        data = await read_valid_upload(file)
        result = app.state.detection_service_provider.get().detect_from_bytes(payload=data, options=options)
        return {"tags": result.tags}

    return app


app = create_app(settings)
