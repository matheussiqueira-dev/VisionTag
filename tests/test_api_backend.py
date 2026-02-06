import base64
import time

from fastapi.testclient import TestClient

from visiontag.api import app, create_app
from visiontag.config import Settings
from visiontag.security import SlidingWindowRateLimiter
from visiontag.schemas import BoundingBox, DetectionItem, DetectionResult


class FakeDetectionService:
    def __init__(self):
        self.calls = 0

    def detect_from_bytes(self, payload, options, **kwargs):
        self.calls += 1
        return DetectionResult(
            tags=["mesa"],
            detections=[
                DetectionItem(
                    label="mesa",
                    confidence=0.88,
                    bbox=BoundingBox(x1=1, y1=1, x2=10, y2=10),
                )
            ],
            total_detections=1,
            inference_ms=5.3,
            cached=False,
        )


class FakeProvider:
    def __init__(self):
        self.service = FakeDetectionService()
        self.model_loaded = True
        self._cache_items = 0

    def get(self):
        return self.service

    def cache_size(self):
        return self._cache_items

    def clear_cache(self):
        removed = self._cache_items
        self._cache_items = 0
        return removed


def test_detect_endpoint_returns_contract():
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/detect",
            files={"file": ("sample.png", b"fake-image", "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tags"] == ["mesa"]
    assert payload["total_detections"] == 1
    assert "X-Request-ID" in response.headers


def test_detect_endpoint_rejects_unsupported_media_type():
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/detect",
            files={"file": ("sample.txt", b"text", "text/plain")},
        )

    assert response.status_code == 415
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_media_type"


def test_admin_metrics_requires_admin_scope():
    with TestClient(app) as client:
        denied = client.get("/api/v1/metrics")
        allowed = client.get("/api/v1/metrics", headers={"X-API-Key": app.state.settings.default_api_key})

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert "requests_total" in allowed.json()
    assert "p95_latency_ms" in allowed.json()


def test_batch_endpoint_returns_summary():
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/detect/batch",
            files=[
                ("files", ("ok.png", b"fake-image", "image/png")),
                ("files", ("bad.txt", b"bad", "text/plain")),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_files"] == 2
    assert payload["summary"]["success"] == 1
    assert payload["summary"]["failed"] == 1


def test_detect_url_endpoint_returns_contract(monkeypatch):
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    async def fake_fetch_remote_image(*, url, timeout_seconds, max_bytes):
        assert url == "https://example.com/camera.png"
        assert timeout_seconds >= 1
        assert max_bytes > 0
        return b"remote-image"

    monkeypatch.setattr("visiontag.api.fetch_remote_image", fake_fetch_remote_image)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/detect/url",
            json={"image_url": "https://example.com/camera.png"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tags"] == ["mesa"]
    assert payload["cached"] is False


def test_detect_base64_endpoint_returns_contract():
    provider = FakeProvider()
    app.state.detection_service_provider = provider
    encoded = base64.b64encode(b"fake-image").decode("ascii")

    with TestClient(app) as client:
        response = client.post("/api/v1/detect/base64", json={"image_base64": encoded})

    assert response.status_code == 200
    payload = response.json()
    assert payload["tags"] == ["mesa"]
    assert payload["total_detections"] == 1


def test_detect_base64_endpoint_rejects_invalid_payload():
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    with TestClient(app) as client:
        response = client.post("/api/v1/detect/base64", json={"image_base64": "%%%not-base64%%%"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_input"


def test_detect_url_batch_endpoint_returns_summary(monkeypatch):
    provider = FakeProvider()
    app.state.detection_service_provider = provider

    async def fake_fetch_remote_image(*, url, timeout_seconds, max_bytes):
        assert timeout_seconds >= 1
        assert max_bytes > 0
        assert url.startswith("https://example.com/")
        return b"remote-image"

    monkeypatch.setattr("visiontag.api.fetch_remote_image", fake_fetch_remote_image)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/detect/url/batch",
            json={
                "image_urls": [
                    "https://example.com/camera-1.png",
                    "https://example.com/camera-2.png",
                ]
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_files"] == 2
    assert payload["summary"]["success"] == 2
    assert payload["summary"]["failed"] == 0


def test_admin_overview_returns_contract():
    provider = FakeProvider()
    provider._cache_items = 7
    app.state.detection_service_provider = provider
    app.state.telemetry.record_analysis(
        source="upload",
        principal_id="tester",
        request_id="req-1",
        tags=["mesa", "cadeira"],
        total_detections=2,
        inference_ms=12.5,
        cached=False,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/overview", headers={"X-API-Key": app.state.settings.default_api_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache_items"] == 7
    assert "metrics" in payload
    assert "runtime" in payload
    assert payload["recent"]["window_size"] >= 1
    assert "sources" in payload["recent"]
    assert isinstance(payload["recent_items"], list)


def test_admin_runtime_returns_new_concurrency_fields():
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/runtime", headers={"X-API-Key": app.state.settings.default_api_key})

    assert response.status_code == 200
    payload = response.json()
    assert "max_concurrent_remote_fetch" in payload
    assert "inference_timeout_seconds" in payload


def test_admin_cache_clear_returns_removed_items():
    provider = FakeProvider()
    provider._cache_items = 4
    app.state.detection_service_provider = provider

    with TestClient(app) as client:
        response = client.delete("/api/v1/admin/cache", headers={"X-API-Key": app.state.settings.default_api_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["removed_items"] == 4


def test_detect_rate_limit_returns_retry_after_header():
    provider = FakeProvider()
    app.state.detection_service_provider = provider
    app.state.rate_limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/detect",
            files={"file": ("sample.png", b"fake-image", "image/png")},
        )
        second = client.post(
            "/api/v1/detect",
            files={"file": ("sample.png", b"fake-image", "image/png")},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_detect_endpoint_returns_processing_timeout_for_slow_inference():
    class SlowService:
        def detect_from_bytes(self, payload, options, **kwargs):
            time.sleep(1.1)
            return DetectionResult(
                tags=["mesa"],
                detections=[
                    DetectionItem(
                        label="mesa",
                        confidence=0.88,
                        bbox=BoundingBox(x1=1, y1=1, x2=10, y2=10),
                    )
                ],
                total_detections=1,
                inference_ms=1100.0,
                cached=False,
            )

    class SlowProvider:
        def __init__(self):
            self.service = SlowService()
            self.model_loaded = True

        def get(self):
            return self.service

        def cache_size(self):
            return 0

        def clear_cache(self):
            return 0

    timeout_app = create_app(Settings(inference_timeout_seconds=1))
    timeout_app.state.detection_service_provider = SlowProvider()

    with TestClient(timeout_app) as client:
        response = client.post(
            "/api/v1/detect",
            files={"file": ("sample.png", b"fake-image", "image/png")},
        )

    assert response.status_code == 504
    payload = response.json()
    assert payload["error"]["code"] == "processing_timeout"
