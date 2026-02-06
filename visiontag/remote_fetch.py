from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from .errors import InvalidInputError, PayloadTooLargeError, UnsupportedMediaTypeError
from .utils import is_allowed_content_type

BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
ALLOWED_PORTS = {80, 443}


def validate_remote_image_url(url: str) -> None:
    parsed = urlsplit(url)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise InvalidInputError("A URL deve usar protocolo http ou https.")

    if not parsed.netloc:
        raise InvalidInputError("URL invalida.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise InvalidInputError("Hostname invalido na URL.")

    if parsed.port is not None and parsed.port not in ALLOWED_PORTS:
        raise InvalidInputError("Porta nao permitida para download remoto.")

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


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    )


def resolve_hostname_ips(hostname: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        records = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise InvalidInputError("Nao foi possivel resolver o hostname informado.") from exc

    resolved_ips: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for record in records:
        address_text = str(record[4][0])
        try:
            resolved_ips.add(ipaddress.ip_address(address_text))
        except ValueError:
            continue

    if not resolved_ips:
        raise InvalidInputError("Hostname sem endereco IP valido.")
    return resolved_ips


async def ensure_hostname_public_resolution(url: str) -> None:
    hostname = (urlsplit(url).hostname or "").strip().lower()
    if not hostname:
        raise InvalidInputError("Hostname invalido na URL.")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ips = await asyncio.to_thread(resolve_hostname_ips, hostname)
        for resolved_ip in ips:
            if _is_forbidden_ip(resolved_ip):
                raise InvalidInputError("Hostname resolve para endereco IP nao permitido.")
        return

    if _is_forbidden_ip(ip):
        raise InvalidInputError("Endereco IP nao permitido por politica de seguranca.")


def validate_response_url_chain(response: httpx.Response) -> None:
    urls = [str(item.request.url) for item in response.history]
    urls.append(str(response.request.url))
    for url in urls:
        validate_remote_image_url(url)


async def fetch_remote_image(
    *,
    url: str,
    timeout_seconds: int,
    max_bytes: int,
) -> bytes:
    validate_remote_image_url(url)
    await ensure_hostname_public_resolution(url)

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

        validate_response_url_chain(response)
        for history_response in response.history:
            await ensure_hostname_public_resolution(str(history_response.request.url))
        await ensure_hostname_public_resolution(str(response.request.url))

        content_length = (response.headers.get("content-length") or "").strip()
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                raise InvalidInputError("Content-Length invalido na resposta remota.")
            if declared_size > max_bytes:
                raise PayloadTooLargeError("Imagem remota excede o limite permitido.")

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
