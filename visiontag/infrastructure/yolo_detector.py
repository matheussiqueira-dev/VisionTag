from __future__ import annotations

from threading import Lock

import numpy as np

from ..core.models import RawDetection


class YoloObjectDetector:
    def __init__(self, model_path: str = "yolov8n.pt") -> None:
        self._model_path = model_path
        self._model = None
        self._lock = Lock()

    def _get_model(self):
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(self._model_path)
        return self._model

    def detect(self, image: np.ndarray, conf_threshold: float) -> list[RawDetection]:
        model = self._get_model()
        with self._lock:
            results = model.predict(image, conf=conf_threshold, verbose=False)

        if not results:
            return []

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        confs = boxes.conf.cpu().tolist()
        classes = boxes.cls.cpu().tolist()
        xyxys = boxes.xyxy.cpu().tolist()
        names = result.names

        detections: list[RawDetection] = []
        for conf, cls_id, xyxy in zip(confs, classes, xyxys):
            cls_idx = int(cls_id)
            label = self._resolve_label(names, cls_idx)
            x1, y1, x2, y2 = xyxy
            detections.append(
                RawDetection(
                    label=label,
                    confidence=float(conf),
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                )
            )
        return detections

    @staticmethod
    def _resolve_label(names, cls_idx: int) -> str:
        if isinstance(names, dict):
            return str(names.get(cls_idx, cls_idx))
        if isinstance(names, (list, tuple)) and 0 <= cls_idx < len(names):
            return str(names[cls_idx])
        return str(cls_idx)

