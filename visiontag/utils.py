from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Tuple

import cv2
import numpy as np

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
}


def is_allowed_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return content_type.lower() in ALLOWED_IMAGE_TYPES


def decode_image(data: bytes):
    if not data:
        return None
    array = np.frombuffer(data, np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def resize_preserving_aspect(image, max_dimension: int) -> Tuple[object, float]:
    if max_dimension <= 0:
        return image, 1.0

    height, width = image.shape[:2]
    largest = max(height, width)
    if largest <= max_dimension:
        return image, 1.0

    scale = max_dimension / float(largest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return resized, scale


def tag_frequency(tags: Iterable[str]) -> Dict[str, int]:
    counts = Counter(tags)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def sanitize_filename(value: str | None) -> str:
    candidate = Path(value or "arquivo").name.strip()
    if not candidate:
        return "arquivo"
    return candidate[:160]


def normalize_labels(labels: Iterable[str] | None) -> tuple[str, ...]:
    if not labels:
        return ()
    cleaned = [label.strip().lower() for label in labels if label and label.strip()]
    return tuple(sorted(set(cleaned)))
