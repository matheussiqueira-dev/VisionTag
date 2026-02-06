from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Dict, List, Tuple

import numpy as np
from ultralytics import YOLO

from .labels_pt import COCO_PT
from .utils import resize_preserving_aspect

_MODEL_CACHE: Dict[str, YOLO] = {}
_MODEL_CACHE_LOCK = Lock()


@dataclass(frozen=True)
class DetectionOptions:
    conf: float = 0.7
    max_tags: int = 5
    min_area_ratio: float = 0.01
    include_person: bool = False

    def normalized(self) -> "DetectionOptions":
        return DetectionOptions(
            conf=min(max(self.conf, 0.01), 1.0),
            max_tags=max(1, int(self.max_tags)),
            min_area_ratio=min(max(self.min_area_ratio, 0.0), 1.0),
            include_person=bool(self.include_person),
        )


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]


@dataclass(frozen=True)
class DetectionSummary:
    tags: List[str]
    detections: List[Detection]
    inference_ms: float


@dataclass
class VisionTagger:
    model_path: str = "yolov8n.pt"
    max_dimension: int = 1280
    _model: YOLO = field(init=False, repr=False)
    _inference_lock: Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._model = self._load_model(self.model_path)
        self._inference_lock = Lock()

    @staticmethod
    def _load_model(model_path: str) -> YOLO:
        with _MODEL_CACHE_LOCK:
            if model_path not in _MODEL_CACHE:
                _MODEL_CACHE[model_path] = YOLO(model_path)
            return _MODEL_CACHE[model_path]

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def _predict(self, image: np.ndarray, options: DetectionOptions) -> Tuple[List[Detection], float]:
        if image is None or image.size == 0:
            raise ValueError("Imagem invalida")

        options = options.normalized()
        height, width = image.shape[:2]
        min_area_px = options.min_area_ratio * float(height * width)

        resized_image, scale = resize_preserving_aspect(image, self.max_dimension)

        started = perf_counter()
        with self._inference_lock:
            results = self._model.predict(resized_image, conf=options.conf, verbose=False)
        elapsed_ms = (perf_counter() - started) * 1000

        if not results:
            return [], elapsed_ms

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return [], elapsed_ms

        confs = boxes.conf.cpu().tolist()
        clss = boxes.cls.cpu().tolist()
        xyxys = boxes.xyxy.cpu().tolist()
        names = result.names or {}

        candidates = sorted(zip(confs, clss, xyxys), key=lambda item: item[0], reverse=True)
        best_by_label: Dict[str, Detection] = {}

        for confidence, cls_id, xyxy in candidates:
            if confidence < options.conf:
                continue

            class_id = int(cls_id)
            label_en = names.get(class_id, str(class_id))
            if not options.include_person and label_en == "person":
                continue

            x1, y1, x2, y2 = [float(value) for value in xyxy]
            if scale != 1.0:
                inv_scale = 1.0 / scale
                x1, y1, x2, y2 = x1 * inv_scale, y1 * inv_scale, x2 * inv_scale, y2 * inv_scale

            x1 = min(max(0.0, x1), float(width))
            y1 = min(max(0.0, y1), float(height))
            x2 = min(max(0.0, x2), float(width))
            y2 = min(max(0.0, y2), float(height))

            area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            if area < min_area_px:
                continue

            label_pt = COCO_PT.get(label_en, label_en)
            detection = Detection(label=label_pt, confidence=float(confidence), bbox=(x1, y1, x2, y2))

            existing = best_by_label.get(label_pt)
            if existing is None or detection.confidence > existing.confidence:
                best_by_label[label_pt] = detection

        detections = sorted(best_by_label.values(), key=lambda item: item.confidence, reverse=True)
        return detections[: options.max_tags], elapsed_ms

    def detect_objects(self, image: np.ndarray, options: DetectionOptions | None = None) -> List[Detection]:
        chosen_options = options or DetectionOptions()
        detections, _ = self._predict(image, chosen_options)
        return detections

    def detect(self, image: np.ndarray, options: DetectionOptions | None = None) -> List[str]:
        detections = self.detect_objects(image, options)
        return [item.label for item in detections]

    def detect_detailed(self, image: np.ndarray, options: DetectionOptions | None = None) -> DetectionSummary:
        chosen_options = options or DetectionOptions()
        detections, inference_ms = self._predict(image, chosen_options)
        tags = [item.label for item in detections]
        return DetectionSummary(tags=tags, detections=detections, inference_ms=inference_ms)
