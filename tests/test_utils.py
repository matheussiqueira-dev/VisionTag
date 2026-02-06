import cv2
import numpy as np

from visiontag.utils import (
    decode_image,
    is_allowed_content_type,
    normalize_labels,
    resize_preserving_aspect,
    sanitize_filename,
    tag_frequency,
)


def test_is_allowed_content_type():
    assert is_allowed_content_type("image/jpeg")
    assert is_allowed_content_type("image/png")
    assert not is_allowed_content_type("application/pdf")
    assert not is_allowed_content_type(None)


def test_resize_preserving_aspect_changes_large_image():
    image = np.zeros((3000, 2000, 3), dtype=np.uint8)
    resized, scale = resize_preserving_aspect(image, max_dimension=1000)

    assert resized.shape[0] == 1000
    assert resized.shape[1] == 666
    assert 0 < scale < 1


def test_tag_frequency_orders_by_count_and_name():
    result = tag_frequency(["mesa", "livro", "mesa", "copo", "livro", "mesa"])
    assert list(result.items()) == [("mesa", 3), ("livro", 2), ("copo", 1)]


def test_decode_image_from_bytes_round_trip():
    image = np.full((50, 50, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok

    decoded = decode_image(encoded.tobytes())
    assert decoded is not None
    assert decoded.shape[:2] == (50, 50)


def test_sanitize_filename_and_label_normalization():
    assert sanitize_filename("..\\folder\\arquivo.png") == "arquivo.png"
    assert sanitize_filename(" ") == "arquivo"
    assert normalize_labels([" Mesa ", "Cadeira", "mesa"]) == ("cadeira", "mesa")
