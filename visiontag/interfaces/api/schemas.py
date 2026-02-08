from __future__ import annotations

from pydantic import BaseModel, Field


class DetectionItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: tuple[float, float, float, float]


class DetectMeta(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    model: str
    latency_ms: float = Field(ge=0.0)


class DetectResponse(BaseModel):
    tags: list[str]
    detections: list[DetectionItem] | None = None
    meta: DetectMeta


class BatchDetectItem(BaseModel):
    filename: str
    tags: list[str]
    detections: list[DetectionItem] | None = None
    error: str | None = None


class BatchDetectMeta(BaseModel):
    processed: int = Field(ge=0)
    failed: int = Field(ge=0)
    model: str
    latency_ms: float = Field(ge=0.0)


class BatchDetectResponse(BaseModel):
    items: list[BatchDetectItem]
    meta: BatchDetectMeta


class ApiConfigResponse(BaseModel):
    api_key_required: bool
    defaults: dict[str, float | int | bool]
    limits: dict[str, int]


class ErrorResponse(BaseModel):
    detail: str

