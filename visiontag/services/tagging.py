from __future__ import annotations

from typing import Mapping

import numpy as np

from ..core.exceptions import InputValidationError, ModelInferenceError
from ..core.models import Detection, DetectionRequest, DetectionResult
from ..core.protocols import ObjectDetector


class TaggingService:
    def __init__(
        self,
        detector: ObjectDetector,
        label_map: Mapping[str, str] | None = None,
    ) -> None:
        self._detector = detector
        self._label_map = {k.lower(): v for k, v in (label_map or {}).items()}

    def analyze(self, image: np.ndarray, request: DetectionRequest) -> DetectionResult:
        self._validate_image(image)
        height, width = image.shape[:2]
        min_area_px = request.min_area_ratio * float(width * height)

        try:
            raw_detections = self._detector.detect(image, conf_threshold=request.conf_threshold)
        except Exception as exc:
            raise ModelInferenceError("Falha ao executar inferencia no modelo.") from exc

        sorted_items = sorted(raw_detections, key=lambda item: item.confidence, reverse=True)

        detections: list[Detection] = []
        tags: list[str] = []
        seen = set()

        for item in sorted_items:
            if item.confidence < request.conf_threshold:
                continue

            label_en = item.label.strip().lower()
            if not request.include_person and label_en == "person":
                continue

            bbox = self._sanitize_bbox(item.bbox, width, height)
            if self._bbox_area(bbox) < min_area_px:
                continue

            label_pt = self._label_map.get(label_en, item.label)
            if label_pt in seen:
                continue

            detections.append(
                Detection(
                    label=label_pt,
                    confidence=float(item.confidence),
                    bbox=bbox,
                )
            )
            tags.append(label_pt)
            seen.add(label_pt)

            if len(tags) >= request.max_tags:
                break

        return DetectionResult(
            tags=tags,
            detections=detections,
            image_width=width,
            image_height=height,
        )

    @staticmethod
    def _validate_image(image: np.ndarray) -> None:
        if image is None:
            raise InputValidationError("Imagem invalida.")
        if not hasattr(image, "shape"):
            raise InputValidationError("Formato de imagem nao suportado.")
        if len(image.shape) < 2 or image.shape[0] <= 0 or image.shape[1] <= 0:
            raise InputValidationError("Dimensoes da imagem sao invalidas.")

    @staticmethod
    def _sanitize_bbox(
        bbox: tuple[float, float, float, float],
        width: int,
        height: int,
    ) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = bbox
        x1 = max(0.0, min(float(width), float(x1)))
        y1 = max(0.0, min(float(height), float(y1)))
        x2 = max(0.0, min(float(width), float(x2)))
        y2 = max(0.0, min(float(height), float(y2)))
        return x1, y1, x2, y2

    @staticmethod
    def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
        x1, y1, x2, y2 = bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

