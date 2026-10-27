
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken,
)
from django.contrib.auth import get_user_model

User = get_user_model()


def blacklist_refresh_token(token: str | None) -> bool:
    """
    Blacklist a refresh token.

    Returns:
        True if blacklisting succeeds, otherwise False.
    """
    if not token:
        return False

    try:
        RefreshToken(token).blacklist()
        return True
    except TokenError:
        return False


def blacklist_all_user_refresh_tokens(user: User) -> None:
    """
    Blacklist all outstanding refresh tokens belonging to a user.
    """
    outstanding_tokens = OutstandingToken.objects.filter(
        user_id=user.pk,
    )

    for token in outstanding_tokens.iterator():
        BlacklistedToken.objects.get_or_create(
            token=token,
        )