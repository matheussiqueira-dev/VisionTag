from __future__ import annotations

import hashlib
import hmac
from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Deque, Dict, Iterable, Optional, Set

from fastapi import Depends, Header, Request

from .config import Settings
from .errors import AuthenticationError, AuthorizationError, RateLimitError


@dataclass(frozen=True)
class ApiPrincipal:
    key_id: str
    scopes: Set[str]


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._auth_required = settings.auth_required
        self._keys: Dict[str, ApiPrincipal] = {}

        for token, scopes in settings.api_keys.items():
            digest = self._digest(token)
            key_id = digest[:12]
            self._keys[digest] = ApiPrincipal(key_id=key_id, scopes=set(scopes))

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def authenticate(self, token: str | None) -> ApiPrincipal:
        if not token:
            if self._auth_required:
                raise AuthenticationError("Chave de API obrigatoria. Use o header X-API-Key.")
            return ApiPrincipal(key_id="anonymous", scopes={"detect"})

        incoming = self._digest(token)
        for expected_digest, principal in self._keys.items():
            if hmac.compare_digest(incoming, expected_digest):
                return principal

        raise AuthenticationError("Chave de API invalida.")

    @property
    def auth_required(self) -> bool:
        return self._auth_required

    def ensure_scopes(self, principal: ApiPrincipal, required_scopes: Iterable[str]) -> None:
        required = {scope.strip().lower() for scope in required_scopes if scope and scope.strip()}
        if not required:
            return

        missing = sorted(required - principal.scopes)
        if missing:
            raise AuthorizationError(f"Permissao insuficiente. Escopos ausentes: {', '.join(missing)}")


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = max(1, limit)
        self._window = max(1, window_seconds)
        self._lock = Lock()
        self._buckets: Dict[str, Deque[float]] = {}

    def check(self, identity: str) -> RateLimitDecision:
        now = monotonic()
        threshold = now - self._window

        with self._lock:
            bucket = self._buckets.setdefault(identity, deque())
            while bucket and bucket[0] <= threshold:
                bucket.popleft()

            if len(bucket) >= self._limit:
                retry_after = int(max(1, self._window - (now - bucket[0])))
                return RateLimitDecision(allowed=False, retry_after=retry_after)

            bucket.append(now)
            return RateLimitDecision(allowed=True, retry_after=0)


def extract_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return token or None

    return None


def require_access(*scopes: str, apply_rate_limit: bool = False):
    async def dependency(request: Request, token: str | None = Depends(extract_api_key)) -> ApiPrincipal:
        auth_service: AuthService = request.app.state.auth_service
        principal = auth_service.authenticate(token)
        auth_service.ensure_scopes(principal, scopes)

        if apply_rate_limit:
            limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
            client_host = request.client.host if request.client else "unknown"
            decision = limiter.check(identity=f"{principal.key_id}:{client_host}")
            if not decision.allowed:
                raise RateLimitError(retry_after=decision.retry_after)

        request.state.principal = principal
        return principal

    return dependency
