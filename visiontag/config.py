from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field


@dataclass
class VisionTagConfig:
    model_path: str = field(default_factory=lambda: os.getenv("VISIONTAG_MODEL", "yolov8n.pt"))
    conf: float = field(default_factory=lambda: float(os.getenv("VISIONTAG_CONF", "0.7")))
    max_tags: int = field(default_factory=lambda: int(os.getenv("VISIONTAG_MAX_TAGS", "5")))
    min_area_ratio: float = field(default_factory=lambda: float(os.getenv("VISIONTAG_MIN_AREA", "0.01")))
    include_person: bool = field(default_factory=lambda: os.getenv("VISIONTAG_INCLUDE_PERSON", "0") == "1")
    api_max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("VISIONTAG_MAX_UPLOAD_MB", "10")) * 1024 * 1024)
    log_level: str = field(default_factory=lambda: os.getenv("VISIONTAG_LOG_LEVEL", "INFO"))

    def __post_init__(self) -> None:
        if not 0.0 < self.conf <= 1.0:
            raise ValueError(f"conf deve estar entre 0 e 1, recebido: {self.conf}")
        if self.max_tags < 1:
            raise ValueError(f"max_tags deve ser >= 1, recebido: {self.max_tags}")
        if not 0.0 <= self.min_area_ratio < 1.0:
            raise ValueError(f"min_area_ratio deve estar entre 0 e 1, recebido: {self.min_area_ratio}")


_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def setup_logging(level: str = "INFO") -> logging.Logger:
    level = level.upper()
    if level not in _ALLOWED_LOG_LEVELS:
        level = "INFO"

    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, level),
    )
    return logging.getLogger("visiontag")


logger = setup_logging(os.getenv("VISIONTAG_LOG_LEVEL", "INFO"))
