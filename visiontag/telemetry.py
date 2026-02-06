from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Deque, Dict, List


@dataclass(frozen=True)
class TelemetrySnapshot:
    uptime_seconds: int
    requests_total: int
    errors_total: int
    detections_total: int
    cache_hits: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_by_path: Dict[str, int]
    requests_by_status_class: Dict[str, int]


@dataclass(frozen=True)
class RecentDetection:
    timestamp: str
    source: str
    principal_id: str
    request_id: str
    tags: List[str]
    total_detections: int
    inference_ms: float
    cached: bool


class TelemetryStore:
    def __init__(self, recent_capacity: int = 150) -> None:
        self._started_at = monotonic()
        self._lock = Lock()
        self._requests_total = 0
        self._errors_total = 0
        self._detections_total = 0
        self._cache_hits = 0
        self._latency_total_ms = 0.0
        self._latency_samples: Deque[float] = deque(maxlen=2048)
        self._requests_by_path: Dict[str, int] = defaultdict(int)
        self._requests_by_status_class: Dict[str, int] = defaultdict(int)
        self._recent_detections: Deque[RecentDetection] = deque(maxlen=max(10, recent_capacity))

    def record_request(self, path: str, status_code: int, latency_ms: float) -> None:
        with self._lock:
            safe_latency = max(0.0, latency_ms)
            self._requests_total += 1
            self._latency_total_ms += safe_latency
            self._latency_samples.append(safe_latency)
            self._requests_by_path[path] += 1
            status_class = f"{max(1, int(status_code)) // 100}xx"
            self._requests_by_status_class[status_class] += 1
            if status_code >= 400:
                self._errors_total += 1

    def record_detection(self, detections_count: int, cached: bool) -> None:
        with self._lock:
            self._detections_total += max(0, detections_count)
            if cached:
                self._cache_hits += 1

    def record_analysis(
        self,
        *,
        source: str,
        principal_id: str,
        request_id: str,
        tags: List[str],
        total_detections: int,
        inference_ms: float,
        cached: bool,
    ) -> None:
        entry = RecentDetection(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            principal_id=principal_id,
            request_id=request_id,
            tags=list(tags),
            total_detections=max(0, total_detections),
            inference_ms=max(0.0, float(inference_ms)),
            cached=bool(cached),
        )
        with self._lock:
            self._recent_detections.appendleft(entry)

    def recent(self, limit: int = 20) -> List[RecentDetection]:
        with self._lock:
            return list(self._recent_detections)[: max(1, limit)]

    def snapshot(self) -> TelemetrySnapshot:
        def percentile(values: List[float], ratio: float) -> float:
            if not values:
                return 0.0
            if len(values) == 1:
                return float(values[0])
            ordered = sorted(values)
            index = int(round((len(ordered) - 1) * ratio))
            index = min(max(index, 0), len(ordered) - 1)
            return float(ordered[index])

        with self._lock:
            uptime = int(monotonic() - self._started_at)
            avg_latency = self._latency_total_ms / self._requests_total if self._requests_total else 0.0
            samples = list(self._latency_samples)
            return TelemetrySnapshot(
                uptime_seconds=uptime,
                requests_total=self._requests_total,
                errors_total=self._errors_total,
                detections_total=self._detections_total,
                cache_hits=self._cache_hits,
                average_latency_ms=round(avg_latency, 2),
                p95_latency_ms=round(percentile(samples, 0.95), 2),
                p99_latency_ms=round(percentile(samples, 0.99), 2),
                requests_by_path=dict(sorted(self._requests_by_path.items())),
                requests_by_status_class=dict(sorted(self._requests_by_status_class.items())),
            )
