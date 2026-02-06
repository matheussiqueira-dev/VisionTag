from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class BoundingBox(BaseModel):
    x1: float = Field(..., ge=0)
    y1: float = Field(..., ge=0)
    x2: float = Field(..., ge=0)
    y2: float = Field(..., ge=0)


class DetectionItem(BaseModel):
    label: str
    confidence: float = Field(..., ge=0, le=1)
    bbox: BoundingBox


class DetectionResult(BaseModel):
    tags: List[str]
    detections: List[DetectionItem]
    total_detections: int = Field(..., ge=0)
    inference_ms: Optional[float] = Field(default=None, ge=0)
    cached: bool = False


class BatchItemResult(BaseModel):
    filename: str
    result: Optional[DetectionResult] = None
    error: Optional[str] = None


class BatchSummary(BaseModel):
    total_files: int = Field(..., ge=0)
    success: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    cached_hits: int = Field(..., ge=0)
    top_tags: Dict[str, int]


class BatchDetectResponse(BaseModel):
    items: List[BatchItemResult]
    summary: BatchSummary


class HealthResponse(BaseModel):
    status: str
    version: str
    model_path: str
    model_loaded: bool
    labels_count: int = Field(..., ge=0)
    auth_required: bool
    rate_limit_per_minute: int = Field(..., ge=1)


class TelemetryResponse(BaseModel):
    uptime_seconds: int = Field(..., ge=0)
    requests_total: int = Field(..., ge=0)
    errors_total: int = Field(..., ge=0)
    detections_total: int = Field(..., ge=0)
    cache_hits: int = Field(..., ge=0)
    average_latency_ms: float = Field(..., ge=0)
    p95_latency_ms: float = Field(..., ge=0)
    p99_latency_ms: float = Field(..., ge=0)
    requests_by_path: Dict[str, int]
    requests_by_status_class: Dict[str, int]


class LabelsResponse(BaseModel):
    total: int = Field(..., ge=0)
    labels: List[str]


class RuntimeSettingsResponse(BaseModel):
    app_name: str
    app_version: str
    auth_required: bool
    rate_limit_per_minute: int = Field(..., ge=1)
    max_upload_mb: int = Field(..., ge=1)
    max_batch_files: int = Field(..., ge=1)
    max_dimension: int = Field(..., ge=1)
    cache_ttl_seconds: int = Field(..., ge=0)
    cache_max_items: int = Field(..., ge=1)
    max_concurrent_inference: int = Field(..., ge=1)
    max_concurrent_remote_fetch: int = Field(..., ge=1)
    inference_timeout_seconds: int = Field(..., ge=1)
    cors_origins: List[str]
    enable_gzip: bool
    remote_fetch_timeout_seconds: int = Field(..., ge=1)
    max_remote_image_mb: int = Field(..., ge=1)


class CacheStatsResponse(BaseModel):
    cache_items: int = Field(..., ge=0)


class CacheClearResponse(BaseModel):
    removed_items: int = Field(..., ge=0)


class DetectUrlRequest(BaseModel):
    image_url: HttpUrl


class DetectBase64Request(BaseModel):
    image_base64: str = Field(..., min_length=4, max_length=20_000_000)
    filename: str | None = Field(default=None, max_length=160)


class BatchUrlDetectRequest(BaseModel):
    image_urls: List[HttpUrl] = Field(..., min_length=1, max_length=25)


class RecentDetectionEntry(BaseModel):
    timestamp: str
    source: str
    principal_id: str
    request_id: str
    tags: List[str]
    total_detections: int = Field(..., ge=0)
    inference_ms: float = Field(..., ge=0)
    cached: bool = False


class RecentDetectionResponse(BaseModel):
    total: int = Field(..., ge=0)
    items: List[RecentDetectionEntry]


class RecentSummary(BaseModel):
    window_size: int = Field(..., ge=0)
    cache_hit_ratio: float = Field(..., ge=0, le=1)
    sources: Dict[str, int]
    top_tags: Dict[str, int]


class AdminOverviewResponse(BaseModel):
    metrics: TelemetryResponse
    runtime: RuntimeSettingsResponse
    cache_items: int = Field(..., ge=0)
    recent: RecentSummary
    recent_items: List[RecentDetectionEntry]
