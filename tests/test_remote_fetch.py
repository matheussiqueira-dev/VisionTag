import asyncio
import httpx
import ipaddress
import pytest

from visiontag.errors import InvalidInputError
from visiontag.remote_fetch import ensure_hostname_public_resolution, validate_remote_image_url, validate_response_url_chain


def test_validate_remote_image_url_accepts_public_https():
    validate_remote_image_url("https://example.com/image.png")


def test_validate_remote_image_url_rejects_localhost():
    with pytest.raises(InvalidInputError):
        validate_remote_image_url("http://localhost/image.png")


def test_validate_remote_image_url_rejects_private_ip():
    with pytest.raises(InvalidInputError):
        validate_remote_image_url("http://192.168.0.10/image.png")


def test_validate_remote_image_url_rejects_non_standard_port():
    with pytest.raises(InvalidInputError):
        validate_remote_image_url("https://example.com:8443/image.png")


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


def test_ensure_hostname_public_resolution_rejects_private_resolved_ip(monkeypatch):
    def fake_resolve_hostname_ips(hostname):
        assert hostname == "safe.example.com"
        return {ipaddress.ip_address("10.20.30.40")}

    monkeypatch.setattr("visiontag.remote_fetch.resolve_hostname_ips", fake_resolve_hostname_ips)

    with pytest.raises(InvalidInputError):
        asyncio.run(ensure_hostname_public_resolution("https://safe.example.com/image.png"))
