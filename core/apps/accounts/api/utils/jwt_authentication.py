from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import PermissionDenied


class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request):
    """
    Enforce Django CSRF validation for cookie-based authentication.
    """
    django_request = request._request

    check = CSRFCheck(lambda req: None)

    check.process_request(django_request)

    reason = check.process_view(
        django_request,
        lambda req: None,
        (),
        {},
    )

    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """
    Supports both Bearer token and HttpOnly access cookie.

    - Authorization header: standard JWT authentication.
    - Access cookie: JWT authentication with CSRF protection.
    """

    def authenticate(self, request):

        header = self.get_header(request)

        # Prefer Authorization header when provided.
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        # Cookie-based authentication requires CSRF protection.
        if header is None:
            enforce_csrf(request)

        return self.get_user(validated_token), validated_token
