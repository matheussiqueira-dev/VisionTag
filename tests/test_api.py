from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_tagger():
    with patch("visiontag.api._tagger") as mock:
        mock.detect_with_scores.return_value = [
            {"tag": "cadeira", "confidence": 0.92, "bbox": [10.0, 10.0, 80.0, 90.0]}
        ]
        yield mock


@pytest.fixture
async def client(mock_tagger):
    from visiontag.api import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_info_returns_config(client):
    resp = await client.get("/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "model" in body
    assert "conf_threshold" in body


@pytest.mark.asyncio
async def test_detect_success(client):
    img_array = np.zeros((100, 100, 3), dtype=np.uint8)
    import cv2
    _, buf = cv2.imencode(".jpg", img_array)
    img_bytes = buf.tobytes()

    resp = await client.post(
        "/detect",
        files={"file": ("test.jpg", BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "tags" in body
    assert "detections" in body
    assert body["tags"] == ["cadeira"]


@pytest.mark.asyncio
async def test_detect_empty_file_returns_400(client):
    resp = await client.post(
        "/detect",
        files={"file": ("empty.jpg", BytesIO(b""), "image/jpeg")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_detect_unsupported_type_returns_415(client):
    resp = await client.post(
        "/detect",
        files={"file": ("doc.pdf", BytesIO(b"fakepdf"), "application/pdf")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_detect_invalid_image_bytes_returns_422(client):
    resp = await client.post(
        "/detect",
        files={"file": ("bad.jpg", BytesIO(b"notanimage"), "image/jpeg")},
    )
    assert resp.status_code == 422
