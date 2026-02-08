from __future__ import annotations

from typing import Protocol

import numpy as np

from .models import RawDetection


class ObjectDetector(Protocol):
    def detect(self, image: np.ndarray, conf_threshold: float) -> list[RawDetection]:
        ...

