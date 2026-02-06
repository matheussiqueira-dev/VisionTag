from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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


class BatchItemResult(BaseModel):
    filename: str
    result: Optional[DetectionResult] = None
    error: Optional[str] = None


class BatchDetectResponse(BaseModel):
    items: List[BatchItemResult]
    summary: Dict[str, int]


class HealthResponse(BaseModel):
    status: str
    model_path: str
    labels_count: int = Field(..., ge=0)
