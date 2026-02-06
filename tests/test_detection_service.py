import cv2
import numpy as np

from visiontag.detector import Detection, DetectionOptions, DetectionSummary
from visiontag.schemas import DetectionResult
from visiontag.services.detection_service import DetectionResultCache, DetectionService
from visiontag.telemetry import TelemetryStore


class FakeTagger:
    def __init__(self):
        self.calls = 0
        self.model_loaded = True

    def detect_detailed(self, image, options):
        self.calls += 1
        detections = [Detection(label="mesa", confidence=0.92, bbox=(1.0, 1.0, 8.0, 8.0))]
        return DetectionSummary(tags=["mesa"], detections=detections, inference_ms=11.7)


def build_valid_image_bytes():
    image = np.full((12, 12, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_detection_service_uses_cache_for_repeated_payload():
    tagger = FakeTagger()
    cache = DetectionResultCache(max_items=32, ttl_seconds=300)
    telemetry = TelemetryStore()
    service = DetectionService(tagger=tagger, cache=cache, telemetry=telemetry)

    payload = build_valid_image_bytes()
    options = DetectionOptions().normalized()

    first = service.detect_from_bytes(payload=payload, options=options)
    second = service.detect_from_bytes(payload=payload, options=options)

    assert isinstance(first, DetectionResult)
    assert first.cached is False
    assert second.cached is True
    assert tagger.calls == 1


def test_detection_service_batch_tracks_success_and_failure():
    tagger = FakeTagger()
    cache = DetectionResultCache(max_items=32, ttl_seconds=300)
    telemetry = TelemetryStore()
    service = DetectionService(tagger=tagger, cache=cache, telemetry=telemetry)

    files = [
        ("ok.png", build_valid_image_bytes()),
        ("bad.png", b"invalid-image-bytes"),
    ]

    response = service.detect_batch(files=files, options=DetectionOptions().normalized())

    assert response.summary.total_files == 2
    assert response.summary.success == 1
    assert response.summary.failed == 1
    assert len(response.items) == 2
    assert response.items[0].result is not None
    assert response.items[1].error is not None
