from visiontag.config import Settings
from visiontag.services.admin_service import AdminReadService
from visiontag.telemetry import TelemetryStore


def test_admin_service_builds_overview_contract():
    telemetry = TelemetryStore()
    telemetry.record_request(path="/api/v1/health", status_code=200, latency_ms=5.0)
    telemetry.record_request(path="/api/v1/detect", status_code=429, latency_ms=13.0)
    telemetry.record_analysis(
        source="upload",
        principal_id="tester",
        request_id="req-1",
        tags=["mesa", "cadeira"],
        total_detections=2,
        inference_ms=11.2,
        cached=False,
    )

    service = AdminReadService(settings=Settings())
    overview = service.build_overview(telemetry=telemetry, cache_items=3, recent_limit=20)

    assert overview.cache_items == 3
    assert overview.metrics.requests_total >= 2
    assert overview.metrics.p95_latency_ms >= 0
    assert "2xx" in overview.metrics.requests_by_status_class
    assert overview.runtime.max_concurrent_inference >= 1
    assert overview.recent.window_size >= 1
