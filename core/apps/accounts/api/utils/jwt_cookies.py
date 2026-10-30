from django.conf import settings
from rest_framework.request import Request


def set_jwt_cookie(response, key, value, lifetime):
    """
    Set a JWT cookie using the project's SIMPLE_JWT cookie settings.
    """
    jwt_settings = settings.SIMPLE_JWT

    response.set_cookie(
        key=key,
        value=value,
        max_age=int(lifetime.total_seconds()),
        path=jwt_settings.get("AUTH_COOKIE_PATH", "/"),
        domain=jwt_settings.get("AUTH_COOKIE_DOMAIN"),
        secure=jwt_settings.get("AUTH_COOKIE_SECURE", not settings.DEBUG),
        httponly=jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True),
        samesite=jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
    )


def delete_jwt_cookie(response, key, *, path=None):
    """
    Delete a cookie using the project's cookie settings.

    Args:
        response: DRF or Django response object.
        key: Cookie name to delete.
        path: Optional cookie path override.
    """
    jwt_settings = settings.SIMPLE_JWT

    response.delete_cookie(
        key=key,
        path=path or jwt_settings.get("AUTH_COOKIE_PATH", "/"),
        domain=jwt_settings.get("AUTH_COOKIE_DOMAIN"),
        samesite=jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
    )


def is_web_client(request: Request) -> bool:
    """
    Identify the client using X-Client-Type.

    Supported values:
        web: Browser-based website using HttpOnly cookies.
        app: Independent applications using JSON tokens.

    If the header is missing, use app behavior for compatibility
    with the default Simple JWT API.
    """
    return request.headers.get("X-Client-Type", "app").lower() == "web"


def get_access_cookie_name() -> str:
    return settings.SIMPLE_JWT["AUTH_COOKIE"]


def get_refresh_cookie_name() -> str:
    return settings.SIMPLE_JWT.get(
        "AUTH_COOKIE_REFRESH",
        "refresh_token",
    )
