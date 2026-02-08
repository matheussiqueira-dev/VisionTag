from __future__ import annotations

import os
from dataclasses import dataclass, field

from .exceptions import InputValidationError


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _to_float(
    value: str | None,
    default: float,
    env_name: str,
    minimum: float,
    maximum: float,
) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise InputValidationError(f"{env_name} deve ser numerico.") from exc
    if not minimum <= parsed <= maximum:
        raise InputValidationError(f"{env_name} deve estar entre {minimum} e {maximum}.")
    return parsed


def _to_int(
    value: str | None,
    default: int,
    env_name: str,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise InputValidationError(f"{env_name} deve ser inteiro.") from exc
    if not minimum <= parsed <= maximum:
        raise InputValidationError(f"{env_name} deve estar entre {minimum} e {maximum}.")
    return parsed


@dataclass(frozen=True)
class AppSettings:
    model_path: str = "yolov8n.pt"
    default_conf: float = 0.7
    default_max_tags: int = 5
    default_min_area_ratio: float = 0.01
    default_include_person: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024
    max_batch_files: int = 10
    api_key: str | None = None
    cors_allow_origins: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> AppSettings:
        max_upload_mb = _to_int(
            os.getenv("VISIONTAG_MAX_UPLOAD_MB"),
            10,
            "VISIONTAG_MAX_UPLOAD_MB",
            1,
            100,
        )
        cors_raw = os.getenv("VISIONTAG_CORS_ORIGINS", "")
        origins = [item.strip() for item in cors_raw.split(",") if item.strip()]
        return cls(
            model_path=os.getenv("VISIONTAG_MODEL", "yolov8n.pt"),
            default_conf=_to_float(
                os.getenv("VISIONTAG_DEFAULT_CONF"),
                0.7,
                "VISIONTAG_DEFAULT_CONF",
                0.0,
                1.0,
            ),
            default_max_tags=_to_int(
                os.getenv("VISIONTAG_DEFAULT_MAX_TAGS"),
                5,
                "VISIONTAG_DEFAULT_MAX_TAGS",
                1,
                50,
            ),
            default_min_area_ratio=_to_float(
                os.getenv("VISIONTAG_DEFAULT_MIN_AREA"),
                0.01,
                "VISIONTAG_DEFAULT_MIN_AREA",
                0.0,
                1.0,
            ),
            default_include_person=_to_bool(
                os.getenv("VISIONTAG_DEFAULT_INCLUDE_PERSON"),
                False,
            ),
            max_upload_bytes=max_upload_mb * 1024 * 1024,
            max_batch_files=_to_int(
                os.getenv("VISIONTAG_MAX_BATCH_FILES"),
                10,
                "VISIONTAG_MAX_BATCH_FILES",
                1,
                100,
            ),
            api_key=(os.getenv("VISIONTAG_API_KEY") or "").strip() or None,
            cors_allow_origins=origins,
        )

