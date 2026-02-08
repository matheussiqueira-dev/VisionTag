from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .core.models import DetectionRequest
from .infrastructure.yolo_detector import YoloObjectDetector
from .labels_pt import COCO_PT
from .services.tagging import TaggingService


@dataclass
class VisionTagger:
    model_path: str = "yolov8n.pt"
    conf: float = 0.7
    max_tags: int = 5
    min_area_ratio: float = 0.01
    include_person: bool = False

    def __post_init__(self) -> None:
        self._service = TaggingService(
            detector=YoloObjectDetector(model_path=self.model_path),
            label_map=COCO_PT,
        )

    def _request(self) -> DetectionRequest:
        return DetectionRequest(
            conf_threshold=self.conf,
            max_tags=self.max_tags,
            min_area_ratio=self.min_area_ratio,
            include_person=self.include_person,
        )

    def detect_objects(self, image) -> List[Tuple[str, float, List[float]]]:
        result = self._service.analyze(image=image, request=self._request())
        return [
            (item.label, item.confidence, [item.bbox[0], item.bbox[1], item.bbox[2], item.bbox[3]])
            for item in result.detections
        ]

    def detect(self, image) -> List[str]:
        result = self._service.analyze(image=image, request=self._request())
        return result.tags
