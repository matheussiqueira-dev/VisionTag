from __future__ import annotations

import asyncio
import base64
import binascii
import logging
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import List
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .detector import DetectionOptions
from .errors import (
    AppError,
    InvalidInputError,
    PayloadTooLargeError,
    ProcessingTimeoutError,
    UnsupportedMediaTypeError,
    register_exception_handlers,
)
from .logging_config import configure_logging
from .remote_fetch import fetch_remote_image
from .schemas import (
    AdminOverviewResponse,
    BatchDetectResponse,
    BatchItemResult,
    BatchSummary,
    CacheClearResponse,
    CacheStatsResponse,
    DetectBase64Request,
    DetectUrlRequest,
    DetectionResult,
    HealthResponse,
    LabelsResponse,
    RecentDetectionEntry,
    RecentDetectionResponse,
    RecentSummary,
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

    telemetry = TelemetryStore(recent_capacity=250)
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
    app.state.inference_semaphore = asyncio.Semaphore(app_settings.max_concurrent_inference)

    cors_origins = list(app_settings.cors_origins) if app_settings.cors_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    if app_settings.enable_gzip:
        app.add_middleware(GZipMiddleware, minimum_size=1024)

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
        except AppError as exc:
            status_code = exc.status_code
            latency_ms = (monotonic() - started) * 1000
            app.state.telemetry.record_request(path=request.url.path, status_code=status_code, latency_ms=latency_ms)
            raise
        except HTTPException as exc:
            status_code = exc.status_code
            latency_ms = (monotonic() - started) * 1000
            app.state.telemetry.record_request(path=request.url.path, status_code=status_code, latency_ms=latency_ms)
            raise
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

    def decode_base64_payload(raw_payload: str) -> bytes:
        candidate = (raw_payload or "").strip()
        if not candidate:
            raise InvalidInputError("Payload base64 vazio.")

        if candidate.lower().startswith("data:"):
            if ";base64," not in candidate:
                raise InvalidInputError("Data URL base64 invalida.")
            prefix, encoded = candidate.split(",", 1)
            declared_content_type = prefix[5:].split(";", 1)[0].strip().lower()
            if declared_content_type and not is_allowed_content_type(declared_content_type):
                raise UnsupportedMediaTypeError("Formato base64 nao suportado.")
            candidate = encoded.strip()

        try:
            decoded = base64.b64decode(candidate, validate=True)
        except binascii.Error as exc:
            raise InvalidInputError("Payload base64 invalido.") from exc

        if not decoded:
            raise InvalidInputError("Payload base64 vazio.")
        if len(decoded) > app_settings.max_upload_bytes:
            raise PayloadTooLargeError(f"Arquivo maior que {app_settings.max_upload_mb} MB.")
        return decoded

    def principal_id_from_request(request: Request) -> str:
        principal = getattr(request.state, "principal", None)
        return getattr(principal, "key_id", "anonymous")

    async def run_detection_inference(
        *,
        payload: bytes,
        options: DetectionOptions,
        source: str,
        principal_id: str,
        request_id: str,
    ) -> DetectionResult:
        service = app.state.detection_service_provider.get()
        async with app.state.inference_semaphore:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(
                        service.detect_from_bytes,
                        payload=payload,
                        options=options,
                        source=source,
                        principal_id=principal_id,
                        request_id=request_id,
                    ),
                    timeout=app_settings.inference_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise ProcessingTimeoutError(
                    f"Tempo limite de inferencia excedido ({app_settings.inference_timeout_seconds}s)."
                ) from exc

    def build_metrics_response() -> TelemetryResponse:
        snapshot = app.state.telemetry.snapshot()
        return TelemetryResponse(
            uptime_seconds=snapshot.uptime_seconds,
            requests_total=snapshot.requests_total,
            errors_total=snapshot.errors_total,
            detections_total=snapshot.detections_total,
            cache_hits=snapshot.cache_hits,
            average_latency_ms=snapshot.average_latency_ms,
            p95_latency_ms=snapshot.p95_latency_ms,
            p99_latency_ms=snapshot.p99_latency_ms,
            requests_by_path=snapshot.requests_by_path,
            requests_by_status_class=snapshot.requests_by_status_class,
        )

    def build_runtime_response() -> RuntimeSettingsResponse:
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
            max_concurrent_inference=app_settings.max_concurrent_inference,
            inference_timeout_seconds=app_settings.inference_timeout_seconds,
            cors_origins=list(app_settings.cors_origins),
            enable_gzip=app_settings.enable_gzip,
            remote_fetch_timeout_seconds=app_settings.remote_fetch_timeout_seconds,
            max_remote_image_mb=app_settings.max_remote_image_mb,
        )

    def build_recent_response(limit: int) -> RecentDetectionResponse:
        entries = app.state.telemetry.recent(limit=limit)
        items = [
            RecentDetectionEntry(
                timestamp=item.timestamp,
                source=item.source,
                principal_id=item.principal_id,
                request_id=item.request_id,
                tags=item.tags,
                total_detections=item.total_detections,
                inference_ms=item.inference_ms,
                cached=item.cached,
            )
            for item in entries
        ]
        return RecentDetectionResponse(total=len(items), items=items)

    def build_recent_summary(limit: int) -> RecentSummary:
        entries = app.state.telemetry.recent(limit=limit)
        source_counts = Counter(item.source for item in entries)
        tag_counts = Counter(tag for item in entries for tag in item.tags)
        cached_hits = sum(1 for item in entries if item.cached)
        cache_hit_ratio = (cached_hits / len(entries)) if entries else 0.0

        return RecentSummary(
            window_size=len(entries),
            cache_hit_ratio=round(cache_hit_ratio, 4),
            sources=dict(sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))),
            top_tags=dict(tag_counts.most_common(8)),
        )

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
        return build_metrics_response()

    @app.get(
        "/api/v1/admin/recent",
        response_model=RecentDetectionResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def recent_detections(limit: int = Query(default=20, ge=1, le=100)) -> RecentDetectionResponse:
        return build_recent_response(limit=limit)

    @app.get(
        "/api/v1/admin/runtime",
        response_model=RuntimeSettingsResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def runtime() -> RuntimeSettingsResponse:
        return build_runtime_response()

    @app.get(
        "/api/v1/admin/overview",
        response_model=AdminOverviewResponse,
        dependencies=[Depends(require_access("admin"))],
    )
    def admin_overview(recent_limit: int = Query(default=30, ge=5, le=200)) -> AdminOverviewResponse:
        recent_response = build_recent_response(limit=min(recent_limit, 12))
        return AdminOverviewResponse(
            metrics=build_metrics_response(),
            runtime=build_runtime_response(),
            cache_items=app.state.detection_service_provider.cache_size(),
            recent=build_recent_summary(limit=recent_limit),
            recent_items=recent_response.items,
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
        request: Request,
        file: UploadFile = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ):
        data = await read_valid_upload(file)
        return await run_detection_inference(
            payload=data,
            options=options,
            source="upload",
            principal_id=principal_id_from_request(request),
            request_id=request.state.request_id,
        )

    @app.post(
        "/api/v1/detect/url",
        response_model=DetectionResult,
        dependencies=[Depends(require_access("detect", apply_rate_limit=True))],
    )
    async def detect_by_url(
        request: Request,
        body: DetectUrlRequest,
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> DetectionResult:
        max_remote_bytes = app_settings.max_remote_image_mb * 1024 * 1024
        payload = await fetch_remote_image(
            url=str(body.image_url),
            timeout_seconds=app_settings.remote_fetch_timeout_seconds,
            max_bytes=max_remote_bytes,
        )
        return await run_detection_inference(
            payload=payload,
            options=options,
            source="remote_url",
            principal_id=principal_id_from_request(request),
            request_id=request.state.request_id,
        )

    @app.post(
        "/api/v1/detect/base64",
        response_model=DetectionResult,
        dependencies=[Depends(require_access("detect", apply_rate_limit=True))],
    )
    async def detect_base64(
        request: Request,
        body: DetectBase64Request,
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> DetectionResult:
        payload = decode_base64_payload(body.image_base64)
        return await run_detection_inference(
            payload=payload,
            options=options,
            source="base64_upload",
            principal_id=principal_id_from_request(request),
            request_id=request.state.request_id,
        )

    @app.post(
        "/api/v1/detect/batch",
        response_model=BatchDetectResponse,
        dependencies=[Depends(require_access("detect", apply_rate_limit=True))],
    )
    async def detect_batch(
        request: Request,
        files: List[UploadFile] = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> BatchDetectResponse:
        if not files:
            raise InvalidInputError("Nenhum arquivo enviado.")
        if len(files) > app_settings.max_batch_files:
            raise InvalidInputError(f"Quantidade maxima de arquivos por lote: {app_settings.max_batch_files}.")

        items: List[BatchItemResult] = []
        all_tags: List[str] = []
        success = 0
        failed = 0
        cached_hits = 0
        principal_id = principal_id_from_request(request)

        async def process_upload(upload: UploadFile) -> tuple[BatchItemResult, List[str], bool]:
            filename = sanitize_filename(upload.filename)
            try:
                payload = await read_valid_upload(upload)
                result = await run_detection_inference(
                    payload=payload,
                    options=options,
                    source="batch_upload",
                    principal_id=principal_id,
                    request_id=request.state.request_id,
                )
                return BatchItemResult(filename=filename, result=result), result.tags, result.cached
            except AppError as exc:
                return BatchItemResult(filename=filename, error=exc.message), [], False

        results = await asyncio.gather(*(process_upload(upload) for upload in files))

        for item, tags, cached in results:
            items.append(item)
            if item.result:
                all_tags.extend(tags)
                success += 1
                if cached:
                    cached_hits += 1
            else:
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
        request: Request,
        file: UploadFile = File(...),
        options: DetectionOptions = Depends(detection_options_dependency),
    ) -> dict:
        data = await read_valid_upload(file)
        result = await run_detection_inference(
            payload=data,
            options=options,
            source="legacy_upload",
            principal_id=principal_id_from_request(request),
            request_id=request.state.request_id,
        )
        return {"tags": result.tags}

    return app


app = create_app(settings)
