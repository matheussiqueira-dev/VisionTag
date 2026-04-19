import pytest
from visiontag.config import VisionTagConfig


def test_defaults():
    cfg = VisionTagConfig()
    assert 0.0 < cfg.conf <= 1.0
    assert cfg.max_tags >= 1
    assert 0.0 <= cfg.min_area_ratio < 1.0


def test_invalid_conf_raises():
    with pytest.raises(ValueError, match="conf"):
        VisionTagConfig(conf=0.0)


def test_invalid_conf_above_one():
    with pytest.raises(ValueError, match="conf"):
        VisionTagConfig(conf=1.5)


def test_invalid_max_tags_raises():
    with pytest.raises(ValueError, match="max_tags"):
        VisionTagConfig(max_tags=0)


def test_invalid_min_area_raises():
    with pytest.raises(ValueError, match="min_area_ratio"):
        VisionTagConfig(min_area_ratio=1.0)
