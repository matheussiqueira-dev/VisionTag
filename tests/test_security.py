from visiontag.config import Settings
from visiontag.security import AuthService, SlidingWindowRateLimiter


def test_auth_service_allows_valid_key():
    settings = Settings(auth_required=True, api_keys={"my-key": {"detect"}})
    service = AuthService(settings)

    principal = service.authenticate("my-key")
    assert "detect" in principal.scopes


def test_auth_service_rejects_missing_when_required():
    settings = Settings(auth_required=True, api_keys={"my-key": {"detect"}})
    service = AuthService(settings)

    try:
        service.authenticate(None)
    except Exception as exc:
        assert exc.__class__.__name__ == "AuthenticationError"
    else:
        raise AssertionError("expected authentication error")


def test_auth_service_returns_anonymous_when_not_required():
    settings = Settings(auth_required=False, api_keys={"my-key": {"detect"}})
    service = AuthService(settings)

    principal = service.authenticate(None)
    assert principal.key_id == "anonymous"
    assert "detect" in principal.scopes


def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

    first = limiter.check("client-1")
    second = limiter.check("client-1")
    third = limiter.check("client-1")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after >= 1
