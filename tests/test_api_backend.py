from fastapi.testclient import TestClient

from visiontag.api import app
from visiontag.schemas import BoundingBox, DetectionItem, DetectionResult


class FakeDetectionService:
    def __init__(self):
        self.calls = 0

    def detect_from_bytes(self, payload, options):
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
