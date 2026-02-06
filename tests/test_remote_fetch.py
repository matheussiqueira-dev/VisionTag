from visiontag.remote_fetch import validate_remote_image_url


def test_validate_remote_image_url_accepts_public_https():
    validate_remote_image_url("https://example.com/image.png")


def test_validate_remote_image_url_rejects_localhost():
    try:
        validate_remote_image_url("http://localhost/image.png")
    except Exception as exc:
        assert exc.__class__.__name__ == "InvalidInputError"
    else:
        raise AssertionError("expected invalid input error")


def test_validate_remote_image_url_rejects_private_ip():
    try:
        validate_remote_image_url("http://192.168.0.10/image.png")
    except Exception as exc:
        assert exc.__class__.__name__ == "InvalidInputError"
    else:
        raise AssertionError("expected invalid input error")
