import unittest

import cv2
import numpy as np
from fastapi.testclient import TestClient

from visiontag.core.models import RawDetection
from visiontag.core.settings import AppSettings
from visiontag.interfaces.api.app import create_app
from visiontag.services.tagging import TaggingService


class FakeDetector:
    def detect(self, image, conf_threshold):
        return [
            RawDetection("book", 0.91, (5, 5, 90, 90)),
            RawDetection("cup", 0.88, (10, 10, 50, 50)),
        ]


def build_test_client() -> TestClient:
    settings = AppSettings(
        model_path="fake.pt",
        default_conf=0.7,
        default_max_tags=5,
        default_min_area_ratio=0.01,
        default_include_person=False,
        max_upload_bytes=2 * 1024 * 1024,
        max_batch_files=4,
        api_key="secret-key",
        cors_allow_origins=[],
    )
    service = TaggingService(
        detector=FakeDetector(),
        label_map={"book": "livro", "cup": "copo"},
    )
    app = create_app(settings=settings, service=service)
    return TestClient(app)


def make_image_bytes() -> bytes:
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Falha ao codificar imagem de teste.")
    return encoded.tobytes()


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = build_test_client()
        cls.image_bytes = make_image_bytes()

    def test_bloqueia_sem_api_key(self):
        response = self.client.post(
            "/api/v1/detect",
            files={"file": ("sample.jpg", self.image_bytes, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 401)

    def test_detect_retorna_tags_e_detalhes(self):
        response = self.client.post(
            "/api/v1/detect?include_details=true",
            headers={"X-API-Key": "secret-key"},
            files={"file": ("sample.jpg", self.image_bytes, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tags"], ["livro", "copo"])
        self.assertEqual(len(payload["detections"]), 2)
        self.assertIn("meta", payload)

    def test_batch_processa_sucesso_e_erro_no_mesmo_lote(self):
        response = self.client.post(
            "/api/v1/detect/batch?include_details=true",
            headers={"X-API-Key": "secret-key"},
            files=[
                ("files", ("ok.jpg", self.image_bytes, "image/jpeg")),
                ("files", ("bad.txt", b"nao-e-imagem", "text/plain")),
            ],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["processed"], 2)
        self.assertEqual(payload["meta"]["failed"], 1)
        self.assertEqual(len(payload["items"]), 2)
        self.assertIn("error", payload["items"][1])


if __name__ == "__main__":
    unittest.main()

