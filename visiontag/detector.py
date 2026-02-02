from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
from ultralytics import YOLO

from .labels_pt import COCO_PT


@dataclass
class VisionTagger:
    model_path: str = "yolov8n.pt"
    conf: float = 0.7
    max_tags: int = 5
    min_area_ratio: float = 0.01
    include_person: bool = False

    def __post_init__(self) -> None:
        self.model = YOLO(self.model_path)

    def detect_objects(self, image) -> List[Tuple[str, float, List[float]]]:
        if image is None:
            raise ValueError("Imagem invalida")

        height, width = image.shape[:2]
        min_area_px = max(0.0, self.min_area_ratio) * float(height * width)

        results = self.model.predict(image, conf=self.conf, verbose=False)
        if not results:
            return []

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        confs = boxes.conf.cpu().tolist()
        clss = boxes.cls.cpu().tolist()
        xyxys = boxes.xyxy.cpu().tolist()

        items = sorted(zip(confs, clss, xyxys), key=lambda x: x[0], reverse=True)

        detections: List[Tuple[str, float, List[float]]] = []
        names = result.names

        for conf, cls_id, xyxy in items:
            if conf < self.conf:
                continue

            cls_id = int(cls_id)
            label_en = names.get(cls_id, str(cls_id))

            if not self.include_person and label_en == "person":
                continue

            if min_area_px > 0:
                x1, y1, x2, y2 = xyxy
                area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                if area < min_area_px:
                    continue

            label_pt = COCO_PT.get(label_en, label_en)
            detections.append((label_pt, float(conf), xyxy))

            if len(detections) >= self.max_tags:
                break

        return detections

    def detect(self, image) -> List[str]:
        detections = self.detect_objects(image)
        tags: List[str] = []
        seen = set()
        for label_pt, _, _ in detections:
            if label_pt in seen:
                continue
            tags.append(label_pt)
            seen.add(label_pt)
        return tags
