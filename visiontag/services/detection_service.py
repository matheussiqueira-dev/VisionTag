from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from time import monotonic
from typing import Dict, Iterable, List, Protocol, Sequence, Tuple

import numpy as np

from ..detector import DetectionOptions, VisionTagger
from ..errors import InvalidInputError
from ..labels_pt import COCO_PT
from ..schemas import BatchDetectResponse, BatchItemResult, BatchSummary, BoundingBox, DetectionItem, DetectionResult
from ..telemetry import TelemetryStore
from ..utils import decode_image, sanitize_filename, tag_frequency


class SupportsDetectionService(Protocol):
    def detect_from_bytes(self, payload: bytes, options: DetectionOptions) -> DetectionResult:
        ...

    def detect_batch(self, files: Sequence[Tuple[str, bytes]], options: DetectionOptions) -> BatchDetectResponse:
        ...


@dataclass(frozen=True)
class CacheEntry:
    expires_at: float
    result: DetectionResult


class DetectionResultCache:
    def __init__(self, max_items: int, ttl_seconds: int) -> None:
        self._max_items = max(16, max_items)
        self._ttl_seconds = max(0, ttl_seconds)
        self._lock = Lock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()

    def _evict_expired(self, now: float) -> None:
        keys_to_remove = [key for key, item in self._entries.items() if item.expires_at <= now]
        for key in keys_to_remove:
            self._entries.pop(key, None)

    def get(self, key: str) -> DetectionResult | None:
        now = monotonic()
        with self._lock:
            self._evict_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry.result.model_copy(deep=True)

    def set(self, key: str, result: DetectionResult) -> None:
        if self._ttl_seconds == 0:
            return

        now = monotonic()
        entry = CacheEntry(expires_at=now + self._ttl_seconds, result=result.model_copy(deep=True))

        with self._lock:
            self._evict_expired(now)
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = entry

            while len(self._entries) > self._max_items:
                self._entries.popitem(last=False)

    def clear(self) -> int:
        with self._lock:
            removed = len(self._entries)
            self._entries.clear()
            return removed

    def size(self) -> int:
        now = monotonic()
        with self._lock:
            self._evict_expired(now)
            return len(self._entries)


def _normalize_label_csv(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    labels = [chunk.strip().lower() for chunk in raw.split(",") if chunk.strip()]
    return tuple(sorted(set(labels)))


class DetectionService:
    def __init__(self, *, tagger: VisionTagger, cache: DetectionResultCache, telemetry: TelemetryStore) -> None:
        self._tagger = tagger
        self._cache = cache
        self._telemetry = telemetry

    @staticmethod
    def _options_key(options: DetectionOptions) -> str:
        normalized = options.normalized()
        include = ",".join(normalized.include_labels)
        exclude = ",".join(normalized.exclude_labels)
        return (
            f"conf={normalized.conf:.4f};max_tags={normalized.max_tags};min_area={normalized.min_area_ratio:.4f};"
            f"include_person={int(normalized.include_person)};include={include};exclude={exclude}"
        )

    def _cache_key(self, payload: bytes, options: DetectionOptions) -> str:
        digest = sha256(payload).hexdigest()
        return f"{digest}:{self._options_key(options)}"

    def _to_response(self, summary, *, cached: bool) -> DetectionResult:
        detections = [
            DetectionItem(
                label=item.label,
                confidence=round(item.confidence, 4),
                bbox=BoundingBox(
                    x1=round(item.bbox[0], 2),
                    y1=round(item.bbox[1], 2),
                    x2=round(item.bbox[2], 2),
                    y2=round(item.bbox[3], 2),
                ),
            )
            for item in summary.detections
        ]

        return DetectionResult(
            tags=summary.tags,
            detections=detections,
            total_detections=len(detections),
            inference_ms=round(summary.inference_ms, 2),
            cached=cached,
        )

    def _predict(self, payload: bytes, options: DetectionOptions) -> DetectionResult:
        if not payload:
            raise InvalidInputError("Arquivo vazio.")

        cache_key = self._cache_key(payload, options)
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            cached_payload = cached_result.model_copy(update={"cached": True})
            self._telemetry.record_detection(detections_count=cached_payload.total_detections, cached=True)
            return cached_payload

        image = decode_image(payload)
        if image is None or not isinstance(image, np.ndarray):
            raise InvalidInputError("Imagem invalida ou corrompida.")

        summary = self._tagger.detect_detailed(image, options)
        result = self._to_response(summary, cached=False)
        self._cache.set(cache_key, result)
        self._telemetry.record_detection(detections_count=result.total_detections, cached=False)
        return result

    def detect_from_bytes(self, payload: bytes, options: DetectionOptions) -> DetectionResult:
        return self._predict(payload=payload, options=options)

    def detect_batch(self, files: Sequence[Tuple[str, bytes]], options: DetectionOptions) -> BatchDetectResponse:
        if not files:
            raise InvalidInputError("Nenhum arquivo enviado.")

        items: List[BatchItemResult] = []
        all_tags: List[str] = []
        success = 0
        failed = 0
        cached_hits = 0

        for filename, payload in files:
            safe_name = sanitize_filename(filename)
            try:
                result = self._predict(payload=payload, options=options)
                items.append(BatchItemResult(filename=safe_name, result=result))
                all_tags.extend(result.tags)
                success += 1
                if result.cached:
                    cached_hits += 1
            except InvalidInputError as exc:
                items.append(BatchItemResult(filename=safe_name, error=exc.message))
                failed += 1

        summary = BatchSummary(
            total_files=len(files),
            success=success,
            failed=failed,
            cached_hits=cached_hits,
            top_tags=tag_frequency(all_tags),
        )

        return BatchDetectResponse(items=items, summary=summary)

    def clear_cache(self) -> int:
        return self._cache.clear()

    def cache_size(self) -> int:
        return self._cache.size()


class DetectionServiceProvider:
    def __init__(self, *, model_path: str, max_dimension: int, cache_max_items: int, cache_ttl_seconds: int, telemetry: TelemetryStore) -> None:
        self._model_path = model_path
        self._max_dimension = max_dimension
        self._cache_max_items = cache_max_items
        self._cache_ttl_seconds = cache_ttl_seconds
        self._telemetry = telemetry

        self._lock = Lock()
        self._service: DetectionService | None = None

    @property
    def model_loaded(self) -> bool:
        return self._service is not None and self._service._tagger.model_loaded  # noqa: SLF001

    def get(self) -> DetectionService:
        if self._service is not None:
            return self._service

        with self._lock:
            if self._service is None:
                tagger = VisionTagger(model_path=self._model_path, max_dimension=self._max_dimension)
                cache = DetectionResultCache(max_items=self._cache_max_items, ttl_seconds=self._cache_ttl_seconds)
                self._service = DetectionService(tagger=tagger, cache=cache, telemetry=self._telemetry)

        return self._service

    def clear_cache(self) -> int:
        service = self.get()
        return service.clear_cache()

    def cache_size(self) -> int:
        service = self.get()
        return service.cache_size()


def build_detection_options(
    *,
    conf: float,
    max_tags: int,
    min_area: float,
    include_person: bool,
    include_labels: str | None,
    exclude_labels: str | None,
) -> DetectionOptions:
    return DetectionOptions(
        conf=conf,
        max_tags=max_tags,
        min_area_ratio=min_area,
        include_person=include_person,
        include_labels=_normalize_label_csv(include_labels),
        exclude_labels=_normalize_label_csv(exclude_labels),
    ).normalized()


def labels_catalog() -> List[str]:
    return sorted(set(COCO_PT.values()))
