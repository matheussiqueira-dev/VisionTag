from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .exceptions import InputValidationError


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class RawDetection:
    label: str
    confidence: float
    bbox: BBox


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: BBox


@dataclass(frozen=True)
class DetectionRequest:
    conf_threshold: float = 0.7
    max_tags: int = 5
    min_area_ratio: float = 0.01
    include_person: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.conf_threshold <= 1.0:
            raise InputValidationError("conf_threshold deve estar entre 0 e 1.")
        if not 1 <= self.max_tags <= 50:
            raise InputValidationError("max_tags deve estar entre 1 e 50.")
        if not 0.0 <= self.min_area_ratio <= 1.0:
            raise InputValidationError("min_area_ratio deve estar entre 0 e 1.")


@dataclass(frozen=True)
class DetectionResult:
    tags: list[str]
    detections: list[Detection]
    image_width: int
    image_height: int

