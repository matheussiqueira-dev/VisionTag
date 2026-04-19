from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from .config import VisionTagConfig
from .labels_pt import translate_label

logger = logging.getLogger(__name__)

Detection = Tuple[str, float, List[float]]


@dataclass
class VisionTagger:
    """Detecta objetos em imagens e retorna tags em português."""

    config: VisionTagConfig = field(default_factory=VisionTagConfig)

    def __post_init__(self) -> None:
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.config.model_path)
            logger.info("Modelo carregado: %s", self.config.model_path)
        except Exception as exc:
            logger.exception("Falha ao carregar modelo '%s'", self.config.model_path)
            raise RuntimeError(f"Não foi possível carregar o modelo: {exc}") from exc

    @property
    def model(self):
        return self._model

    def _is_valid_image(self, image: np.ndarray) -> bool:
        return image is not None and isinstance(image, np.ndarray) and image.ndim in (2, 3) and image.size > 0

    def detect_objects(self, image: np.ndarray) -> List[Detection]:
        """Retorna lista de (label_pt, confiança, bbox) ordenada por confiança."""
        if not self._is_valid_image(image):
            raise ValueError("Imagem inválida ou vazia")

        height, width = image.shape[:2]
        min_area_px = max(0.0, self.config.min_area_ratio) * float(height * width)

        try:
            results = self._model.predict(image, conf=self.config.conf, verbose=False)
        except Exception as exc:
            logger.exception("Erro durante a predição do modelo")
            raise RuntimeError("Falha na predição") from exc

        if not results:
            return []

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        confs = boxes.conf.cpu().tolist()
        clss = boxes.cls.cpu().tolist()
        xyxys = boxes.xyxy.cpu().tolist()
        names = result.names

        items = sorted(zip(confs, clss, xyxys), key=lambda x: x[0], reverse=True)

        detections: List[Detection] = []
        seen_labels: set[str] = set()

        for conf, cls_id, xyxy in items:
            if conf < self.config.conf:
                continue

            cls_id = int(cls_id)
            label_en = names.get(cls_id, str(cls_id))

            if not self.config.include_person and label_en == "person":
                continue

            if min_area_px > 0:
                x1, y1, x2, y2 = xyxy
                area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                if area < min_area_px:
                    continue

            label_pt = translate_label(label_en)

            if label_pt not in seen_labels:
                detections.append((label_pt, float(conf), xyxy))
                seen_labels.add(label_pt)

            if len(detections) >= self.config.max_tags:
                break

        logger.debug("Detectados %d objeto(s) na imagem", len(detections))
        return detections

    def detect(self, image: np.ndarray) -> List[str]:
        """Retorna somente os nomes das tags detectadas."""
        return [label for label, _, _ in self.detect_objects(image)]

    def detect_with_scores(self, image: np.ndarray) -> List[dict]:
        """Retorna tags com confiança e coordenadas de bounding box."""
        return [
            {"tag": label, "confidence": round(conf, 4), "bbox": [round(v, 1) for v in xyxy]}
            for label, conf, xyxy in self.detect_objects(image)
        ]
