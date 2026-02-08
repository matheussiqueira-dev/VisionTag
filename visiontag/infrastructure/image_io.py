from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from ..core.exceptions import InputValidationError


SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def decode_image_bytes(
    data: bytes,
    content_type: str | None,
    max_upload_bytes: int,
):
    if not data:
        raise InputValidationError("Arquivo vazio.")
    if len(data) > max_upload_bytes:
        size_mb = max_upload_bytes / (1024 * 1024)
        raise InputValidationError(f"Arquivo excede limite de {size_mb:.1f} MB.")
    if content_type:
        parsed_content_type = content_type.split(";")[0].strip().lower()
        if parsed_content_type not in SUPPORTED_CONTENT_TYPES:
            raise InputValidationError(
                "Tipo de arquivo nao suportado. Envie JPG, PNG, WEBP ou BMP."
            )

    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise InputValidationError("Arquivo enviado nao e uma imagem valida.")
    return image


def load_image_file(path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise InputValidationError(f"Nao foi possivel carregar a imagem: {path}")
    return image


def is_supported_image_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS

