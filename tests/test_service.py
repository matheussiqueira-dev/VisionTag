import unittest

import numpy as np

from visiontag.core.exceptions import InputValidationError
from visiontag.core.models import DetectionRequest, RawDetection
from visiontag.services.tagging import TaggingService


class FakeDetector:
    def __init__(self, detections):
        self._detections = detections

    def detect(self, image, conf_threshold):
        return list(self._detections)


class TaggingServiceTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((100, 100, 3), dtype=np.uint8)
        self.label_map = {
            "person": "pessoa",
            "book": "livro",
            "cup": "copo",
            "dog": "cachorro",
        }

    def test_aplica_filtros_de_area_pessoa_e_unicidade(self):
        detections = [
            RawDetection("person", 0.99, (0, 0, 100, 100)),
            RawDetection("book", 0.95, (0, 0, 60, 60)),
            RawDetection("book", 0.90, (10, 10, 40, 40)),
            RawDetection("cup", 0.85, (1, 1, 5, 5)),
        ]
        service = TaggingService(FakeDetector(detections), self.label_map)
        request = DetectionRequest(
            conf_threshold=0.7,
            max_tags=5,
            min_area_ratio=0.01,
            include_person=False,
        )

        result = service.analyze(self.image, request)

        self.assertEqual(result.tags, ["livro"])
        self.assertEqual(len(result.detections), 1)
        self.assertEqual(result.image_width, 100)
        self.assertEqual(result.image_height, 100)

    def test_respeita_max_tags(self):
        detections = [
            RawDetection("person", 0.95, (0, 0, 100, 100)),
            RawDetection("book", 0.94, (0, 0, 90, 90)),
            RawDetection("dog", 0.93, (0, 0, 80, 80)),
        ]
        service = TaggingService(FakeDetector(detections), self.label_map)
        request = DetectionRequest(
            conf_threshold=0.5,
            max_tags=2,
            min_area_ratio=0.0,
            include_person=True,
        )

        result = service.analyze(self.image, request)

        self.assertEqual(result.tags, ["pessoa", "livro"])
        self.assertEqual(len(result.detections), 2)

    def test_rejeita_imagem_invalida(self):
        service = TaggingService(FakeDetector([]), self.label_map)
        request = DetectionRequest()

        with self.assertRaises(InputValidationError):
            service.analyze(None, request)


if __name__ == "__main__":
    unittest.main()

