from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from visiontag.config import VisionTagConfig
from visiontag.detector import VisionTagger


def _make_tagger(include_person=False, conf=0.7, max_tags=5, min_area_ratio=0.0):
    config = VisionTagConfig(
        conf=conf,
        max_tags=max_tags,
        min_area_ratio=min_area_ratio,
        include_person=include_person,
    )
    with patch("visiontag.detector.YOLO") as mock_yolo_cls:
        mock_yolo_cls.return_value = MagicMock()
        tagger = VisionTagger(config=config)
    return tagger


def _make_result(detections):
    """detections: list of (conf, cls_id, label, x1, y1, x2, y2)"""
    import torch

    mock_result = MagicMock()
    mock_result.names = {d[1]: d[2] for d in detections}

    mock_boxes = MagicMock()
    mock_boxes.conf.cpu.return_value.tolist.return_value = [d[0] for d in detections]
    mock_boxes.cls.cpu.return_value.tolist.return_value = [float(d[1]) for d in detections]
    mock_boxes.xyxy.cpu.return_value.tolist.return_value = [[d[3], d[4], d[5], d[6]] for d in detections]
    mock_result.boxes = mock_boxes

    return mock_result


def _blank_image(h=100, w=100):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_detect_objects_returns_portuguese_labels():
    tagger = _make_tagger()
    mock_result = _make_result([(0.9, 0, "car", 10, 10, 50, 50)])
    tagger._model.predict.return_value = [mock_result]

    detections = tagger.detect_objects(_blank_image())
    assert len(detections) == 1
    assert detections[0][0] == "carro"
    assert detections[0][1] == pytest.approx(0.9)


def test_detect_returns_only_tags():
    tagger = _make_tagger()
    mock_result = _make_result([(0.9, 0, "car", 10, 10, 50, 50)])
    tagger._model.predict.return_value = [mock_result]

    tags = tagger.detect(_blank_image())
    assert tags == ["carro"]


def test_person_excluded_by_default():
    tagger = _make_tagger(include_person=False)
    mock_result = _make_result([(0.95, 0, "person", 0, 0, 100, 100)])
    tagger._model.predict.return_value = [mock_result]

    tags = tagger.detect(_blank_image())
    assert "pessoa" not in tags


def test_person_included_when_flag_set():
    tagger = _make_tagger(include_person=True)
    mock_result = _make_result([(0.95, 0, "person", 0, 0, 100, 100)])
    tagger._model.predict.return_value = [mock_result]

    tags = tagger.detect(_blank_image())
    assert "pessoa" in tags


def test_max_tags_respected():
    tagger = _make_tagger(max_tags=2)
    mock_result = _make_result([
        (0.95, 0, "car", 0, 0, 50, 50),
        (0.90, 1, "dog", 0, 0, 50, 50),
        (0.85, 2, "cat", 0, 0, 50, 50),
    ])
    tagger._model.predict.return_value = [mock_result]

    detections = tagger.detect_objects(_blank_image())
    assert len(detections) == 2


def test_duplicate_labels_deduplicated():
    tagger = _make_tagger(max_tags=5)
    mock_result = _make_result([
        (0.95, 0, "car", 0, 0, 50, 50),
        (0.90, 0, "car", 60, 0, 100, 50),
    ])
    tagger._model.predict.return_value = [mock_result]

    detections = tagger.detect_objects(_blank_image())
    labels = [d[0] for d in detections]
    assert labels.count("carro") == 1


def test_invalid_image_raises():
    tagger = _make_tagger()
    with pytest.raises(ValueError, match="Imagem"):
        tagger.detect_objects(None)


def test_detect_with_scores_structure():
    tagger = _make_tagger()
    mock_result = _make_result([(0.88, 0, "laptop", 5, 5, 80, 80)])
    tagger._model.predict.return_value = [mock_result]

    scores = tagger.detect_with_scores(_blank_image())
    assert len(scores) == 1
    assert scores[0]["tag"] == "laptop"
    assert "confidence" in scores[0]
    assert "bbox" in scores[0]
    assert len(scores[0]["bbox"]) == 4


def test_low_confidence_detection_filtered():
    tagger = _make_tagger(conf=0.8)
    mock_result = _make_result([(0.75, 0, "car", 0, 0, 50, 50)])
    tagger._model.predict.return_value = [mock_result]

    detections = tagger.detect_objects(_blank_image())
    assert len(detections) == 0
