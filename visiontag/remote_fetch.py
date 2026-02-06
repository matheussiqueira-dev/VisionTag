from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

import httpx

from .errors import InvalidInputError, PayloadTooLargeError, UnsupportedMediaTypeError
from .utils import is_allowed_content_type

BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


def validate_remote_image_url(url: str) -> None:
    parsed = urlsplit(url)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise InvalidInputError("A URL deve usar protocolo http ou https.")

    if not parsed.netloc:
        raise InvalidInputError("URL invalida.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise InvalidInputError("Hostname invalido na URL.")

    if hostname in BLOCKED_HOSTS or hostname.endswith(".local"):
        raise InvalidInputError("Hostname bloqueado por politica de seguranca.")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise InvalidInputError("Endereco IP nao permitido por politica de seguranca.")


async def fetch_remote_image(
    *,
    url: str,
    timeout_seconds: int,
    max_bytes: int,
) -> bytes:
    validate_remote_image_url(url)

    timeout = httpx.Timeout(timeout=float(timeout_seconds))
    headers = {"User-Agent": "VisionTag/2.2 (+remote-image-fetch)"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True, max_redirects=3) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise InvalidInputError("Timeout ao baixar imagem remota.") from exc
        except httpx.HTTPStatusError as exc:
            raise InvalidInputError(f"Falha ao baixar imagem remota (status {exc.response.status_code}).") from exc
        except httpx.HTTPError as exc:
            raise InvalidInputError("Falha de rede ao acessar URL informada.") from exc

        content_type = (response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if not is_allowed_content_type(content_type):
            raise UnsupportedMediaTypeError("A URL nao retornou um formato de imagem suportado.")

        data = bytearray()
        async for chunk in response.aiter_bytes():
            if chunk:
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise PayloadTooLargeError("Imagem remota excede o limite permitido.")

        if not data:
            raise InvalidInputError("A URL retornou conteudo vazio.")

        return bytes(data)
