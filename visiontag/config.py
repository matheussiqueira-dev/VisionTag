from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple


DEFAULT_SCOPES = {"detect", "admin"}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int, minimum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, parsed)


def _parse_csv(value: str | None) -> Tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item and item.strip())


def parse_api_keys(raw: str | None, fallback_key: str) -> Dict[str, Set[str]]:
    entries: Dict[str, Set[str]] = {}
    if raw:
        chunks = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
        for chunk in chunks:
            if ":" in chunk:
                key, scopes_raw = chunk.split(":", 1)
                key = key.strip()
                scopes = {scope.strip().lower() for scope in scopes_raw.split("|") if scope.strip()}
            else:
                key = chunk
                scopes = {"detect"}

            if not key:
                continue

            if not scopes:
                scopes = {"detect"}

            if "admin" in scopes:
                scopes.add("detect")

            entries[key] = scopes

    if not entries and fallback_key:
        entries[fallback_key] = set(DEFAULT_SCOPES)

    return entries


@dataclass(frozen=True)
class Settings:
    app_name: str = "VisionTag API"
    app_version: str = "2.1.0"
    model_path: str = "yolov8n.pt"
    max_upload_mb: int = 8
    max_dimension: int = 1280
    max_batch_files: int = 10
    cache_ttl_seconds: int = 300
    cache_max_items: int = 256
    auth_required: bool = False
    default_api_key: str = "visiontag-local-dev-key"
    api_keys: Dict[str, Set[str]] = field(default_factory=dict)
    rate_limit_per_minute: int = 120
    log_level: str = "INFO"
    max_concurrent_inference: int = 2
    max_concurrent_remote_fetch: int = 4
    inference_timeout_seconds: int = 25
    cors_origins: Tuple[str, ...] = ("*",)
    enable_gzip: bool = True
    remote_fetch_timeout_seconds: int = 8
    max_remote_image_mb: int = 8

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        fallback_key = os.getenv("VISIONTAG_DEFAULT_API_KEY", "visiontag-local-dev-key")
        api_keys = parse_api_keys(os.getenv("VISIONTAG_API_KEYS"), fallback_key=fallback_key)

        return cls(
            app_name=os.getenv("VISIONTAG_APP_NAME", "VisionTag API"),
            app_version=os.getenv("VISIONTAG_APP_VERSION", "2.1.0"),
            model_path=os.getenv("VISIONTAG_MODEL_PATH", "yolov8n.pt"),
            max_upload_mb=_parse_int(os.getenv("VISIONTAG_MAX_UPLOAD_MB"), default=8, minimum=1),
            max_dimension=_parse_int(os.getenv("VISIONTAG_MAX_DIMENSION"), default=1280, minimum=128),
            max_batch_files=_parse_int(os.getenv("VISIONTAG_MAX_BATCH_FILES"), default=10, minimum=1),
            cache_ttl_seconds=_parse_int(os.getenv("VISIONTAG_CACHE_TTL_SECONDS"), default=300, minimum=0),
            cache_max_items=_parse_int(os.getenv("VISIONTAG_CACHE_MAX_ITEMS"), default=256, minimum=16),
            auth_required=_parse_bool(os.getenv("VISIONTAG_AUTH_REQUIRED"), default=False),
            default_api_key=fallback_key,
            api_keys=api_keys,
            rate_limit_per_minute=_parse_int(os.getenv("VISIONTAG_RATE_LIMIT_PER_MINUTE"), default=120, minimum=10),
            log_level=os.getenv("VISIONTAG_LOG_LEVEL", "INFO").upper(),
            max_concurrent_inference=_parse_int(os.getenv("VISIONTAG_MAX_CONCURRENT_INFERENCE"), default=2, minimum=1),
            max_concurrent_remote_fetch=_parse_int(
                os.getenv("VISIONTAG_MAX_CONCURRENT_REMOTE_FETCH"),
                default=4,
                minimum=1,
            ),
            inference_timeout_seconds=_parse_int(
                os.getenv("VISIONTAG_INFERENCE_TIMEOUT_SECONDS"),
                default=25,
                minimum=1,
            ),
            cors_origins=_parse_csv(os.getenv("VISIONTAG_CORS_ORIGINS", "*")),
            enable_gzip=_parse_bool(os.getenv("VISIONTAG_ENABLE_GZIP"), default=True),
            remote_fetch_timeout_seconds=_parse_int(
                os.getenv("VISIONTAG_REMOTE_FETCH_TIMEOUT_SECONDS"),
                default=8,
                minimum=1,
            ),
            max_remote_image_mb=_parse_int(os.getenv("VISIONTAG_MAX_REMOTE_IMAGE_MB"), default=8, minimum=1),
        )
