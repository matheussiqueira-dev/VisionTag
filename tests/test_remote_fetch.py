import httpx
import pytest

from visiontag.errors import InvalidInputError
from visiontag.remote_fetch import validate_remote_image_url, validate_response_url_chain


def test_validate_remote_image_url_accepts_public_https():
    validate_remote_image_url("https://example.com/image.png")


def test_validate_remote_image_url_rejects_localhost():
    with pytest.raises(InvalidInputError):
        validate_remote_image_url("http://localhost/image.png")


def test_validate_remote_image_url_rejects_private_ip():
    with pytest.raises(InvalidInputError):
        validate_remote_image_url("http://192.168.0.10/image.png")


def test_validate_response_url_chain_rejects_unsafe_redirect():
    first_request = httpx.Request("GET", "https://example.com/image.png")
    redirect_response = httpx.Response(
        status_code=302,
        headers={"location": "http://localhost/image.png"},
        request=first_request,
    )
    final_request = httpx.Request("GET", "http://localhost/image.png")
    final_response = httpx.Response(status_code=200, request=final_request, history=[redirect_response])

    with pytest.raises(InvalidInputError):
        validate_response_url_chain(final_response)
