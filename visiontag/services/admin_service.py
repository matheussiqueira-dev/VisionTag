from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from ..config import Settings
from ..schemas import (
    AdminOverviewResponse,
    RecentDetectionEntry,
    RecentDetectionResponse,
    RecentSummary,
    RuntimeSettingsResponse,
    TelemetryResponse,
)
from ..telemetry import RecentDetection, TelemetrySnapshot, TelemetryStore


@dataclass
class AdminReadService:
    settings: Settings

    def metrics_from_snapshot(self, snapshot: TelemetrySnapshot) -> TelemetryResponse:
        return TelemetryResponse(
            uptime_seconds=snapshot.uptime_seconds,
            requests_total=snapshot.requests_total,
            errors_total=snapshot.errors_total,
            detections_total=snapshot.detections_total,
            cache_hits=snapshot.cache_hits,
            average_latency_ms=snapshot.average_latency_ms,
            p95_latency_ms=snapshot.p95_latency_ms,
            p99_latency_ms=snapshot.p99_latency_ms,
            requests_by_path=snapshot.requests_by_path,
            requests_by_status_class=snapshot.requests_by_status_class,
        )

    def runtime_settings(self) -> RuntimeSettingsResponse:
        settings = self.settings
        return RuntimeSettingsResponse(
            app_name=settings.app_name,
            app_version=settings.app_version,
            auth_required=settings.auth_required,
            rate_limit_per_minute=settings.rate_limit_per_minute,
            max_upload_mb=settings.max_upload_mb,
            max_batch_files=settings.max_batch_files,
            max_dimension=settings.max_dimension,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            cache_max_items=settings.cache_max_items,
            max_concurrent_inference=settings.max_concurrent_inference,
            max_concurrent_remote_fetch=settings.max_concurrent_remote_fetch,
            inference_timeout_seconds=settings.inference_timeout_seconds,
            cors_origins=list(settings.cors_origins),
            enable_gzip=settings.enable_gzip,
            remote_fetch_timeout_seconds=settings.remote_fetch_timeout_seconds,
            max_remote_image_mb=settings.max_remote_image_mb,
        )

    def recent_detection_response(self, entries: Sequence[RecentDetection]) -> RecentDetectionResponse:
        items = [
            RecentDetectionEntry(
                timestamp=item.timestamp,
                source=item.source,
                principal_id=item.principal_id,
                request_id=item.request_id,
                tags=item.tags,
                total_detections=item.total_detections,
                inference_ms=item.inference_ms,
                cached=item.cached,
            )
            for item in entries
        ]
        return RecentDetectionResponse(total=len(items), items=items)

    def recent_summary(self, entries: Sequence[RecentDetection]) -> RecentSummary:
        source_counts = Counter(item.source for item in entries)
        tag_counts = Counter(tag for item in entries for tag in item.tags)
        cached_hits = sum(1 for item in entries if item.cached)
        cache_hit_ratio = (cached_hits / len(entries)) if entries else 0.0

        return RecentSummary(
            window_size=len(entries),
            cache_hit_ratio=round(cache_hit_ratio, 4),
            sources=dict(sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))),
            top_tags=dict(tag_counts.most_common(8)),
        )

    def build_overview(
        self,
        *,
        telemetry: TelemetryStore,
        cache_items: int,
        recent_limit: int,
        recent_items_limit: int = 12,
    ) -> AdminOverviewResponse:
        snapshot = telemetry.snapshot()
        recent_entries = telemetry.recent(limit=recent_limit)
        recent_items = self.recent_detection_response(recent_entries[: max(1, recent_items_limit)]).items
        recent_summary = self.recent_summary(recent_entries)

        return AdminOverviewResponse(
            metrics=self.metrics_from_snapshot(snapshot),
            runtime=self.runtime_settings(),
            cache_items=max(0, cache_items),
            recent=recent_summary,
            recent_items=recent_items,
        )
