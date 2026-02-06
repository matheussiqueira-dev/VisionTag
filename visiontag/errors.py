from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("visiontag.errors")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class AuthenticationError(AppError):
    def __init__(self, message: str = "Nao autenticado."):
        super().__init__(status_code=401, code="authentication_error", message=message)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Acesso negado para este recurso."):
        super().__init__(status_code=403, code="authorization_error", message=message)


class RateLimitError(AppError):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            code="rate_limit_exceeded",
            message="Limite de requisicoes excedido.",
            details={"retry_after": retry_after},
        )


class InvalidInputError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(status_code=400, code="invalid_input", message=message, details=details)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str = "Formato de arquivo nao suportado."):
        super().__init__(status_code=415, code="unsupported_media_type", message=message)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str):
        super().__init__(status_code=413, code="payload_too_large", message=message)


class ProcessingTimeoutError(AppError):
    def __init__(self, message: str = "Tempo limite de processamento excedido."):
        super().__init__(status_code=504, code="processing_timeout", message=message)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = {
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details,
        }
    }
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        headers = None
        if exc.code == "rate_limit_exceeded" and isinstance(exc.details, dict):
            retry_after = exc.details.get("retry_after")
            if retry_after is not None:
                headers = {"Retry-After": str(retry_after)}
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=_request_id(request),
            headers=headers,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Erro HTTP."
        return error_response(
            status_code=exc.status_code,
            code="http_error",
            message=message,
            details=None if isinstance(detail, str) else detail,
            request_id=_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return error_response(
            status_code=422,
            code="validation_error",
            message="Dados de entrada invalidos.",
            details=exc.errors(),
            request_id=_request_id(request),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled application exception", exc_info=exc)
        return error_response(
            status_code=500,
            code="internal_error",
            message="Erro interno do servidor.",
            details=None,
            request_id=_request_id(request),
        )
