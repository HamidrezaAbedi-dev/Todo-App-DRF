import pytest

from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Profile


User = get_user_model()

REGISTER_URL = "/accounts/api/v1/register/"
LOGIN_URL = "/accounts/api/v1/login/"
REFRESH_URL = "/accounts/api/v1/refresh-token/"
VERIFY_URL = "/accounts/api/v1/session/verify/"
LOGOUT_URL = "/accounts/api/v1/logout/"
PASSWORD_URL = "/accounts/api/v1/change-password/"
PROFILE_URL = "/accounts/api/v1/users/me/"
DELETE_ACCOUNT_URL = "/accounts/api/v1/users/me/delete-account/"
CSRF_URL = "/accounts/api/v1/csrf/"

DEFAULT_PASSWORD = "Strong#TodoPass123"
NEW_PASSWORD = "Another#StrongPass456"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="member@example.com",
        password=DEFAULT_PASSWORD,
    )


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def csrf_client():
    return APIClient(enforce_csrf_checks=True)


def prepare_web_client(client):
    """
    Get a CSRF token and prepare headers for browser requests.
    """

    headers = {
        "HTTP_X_CLIENT_TYPE": "web",
    }

    response = client.get(
        CSRF_URL,
        **headers,
    )

    assert response.status_code == 200

    csrf_token = response.data["csrfToken"]
    headers["HTTP_X_CSRFTOKEN"] = csrf_token

    return headers


@pytest.mark.django_db
def test_register_creates_user_and_profile(client):
    response = client.post(
        REGISTER_URL,
        {
            "email": "new@example.com",
            "password": "Secure#Password789",
            "password1": "Secure#Password789",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["email"] == "new@example.com"

    user = User.objects.get(email="new@example.com")

    assert Profile.objects.filter(user=user).exists()
    assert "password" not in response.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("password", "confirmation"),
    [
        ("Secure#Password789", "Different#Password789"),
        ("short", "short"),
    ],
)
def test_register_rejects_mismatched_or_weak_passwords(
    client, password, confirmation
):
    response = client.post(
        REGISTER_URL,
        {
            "email": "invalid@example.com",
            "password": password,
            "password1": confirmation,
        },
        format="json",
    )

    assert response.status_code == 400

    assert not User.objects.filter(
        email="invalid@example.com"
    ).exists()


@pytest.mark.django_db
def test_register_rejects_duplicate_email(client, user):
    response = client.post(
        REGISTER_URL,
        {
            "email": user.email,
            "password": "Secure#Password789",
            "password1": "Secure#Password789",
        },
        format="json",
    )

    assert response.status_code == 400

    assert User.objects.filter(email=user.email).count() == 1


@pytest.mark.django_db
def test_app_login_verify_refresh_and_logout(client, user):
    # Login
    login_response = client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
        format="json",
    )

    assert login_response.status_code == 200

    access_token = login_response.data["access"]
    refresh_token = login_response.data["refresh"]

    # Verify access token
    verify_response = client.post(
        VERIFY_URL,
        {"token": access_token},
        format="json",
    )

    assert verify_response.status_code == 200
    assert verify_response.data == {
        "detail": "Token is valid."
    }

    # Refresh tokens
    refresh_response = client.post(
        REFRESH_URL,
        {"refresh": refresh_token},
        format="json",
    )

    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data

    # When rotation is enabled, use the newly issued refresh token.
    current_refresh_token = refresh_response.data.get(
        "refresh",
        refresh_token,
    )

    # Logout
    logout_response = client.post(
        LOGOUT_URL,
        {"refresh": current_refresh_token},
        format="json",
    )

    assert logout_response.status_code == 200

    # The revoked refresh token must not be usable again.
    invalid_refresh_response = client.post(
        REFRESH_URL,
        {"refresh": current_refresh_token},
        format="json",
    )

    assert invalid_refresh_response.status_code in (400, 401)


@pytest.mark.django_db
def test_login_rejects_invalid_credentials(client, user):
    response = client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": "incorrect-password",
        },
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_web_login_requires_csrf(csrf_client, user):
    response = csrf_client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
        format="json",
        HTTP_X_CLIENT_TYPE="web",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_web_authentication_uses_http_only_cookies(csrf_client, user):
    headers = prepare_web_client(csrf_client)

    # Login
    login_response = csrf_client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
        format="json",
        **headers,
    )

    assert login_response.status_code == 200

    assert "access" not in login_response.data
    assert "refresh" not in login_response.data

    assert login_response.cookies["access_token"]["httponly"]
    assert login_response.cookies["refresh_token"]["httponly"]

    # Verify using access cookie
    verify_response = csrf_client.post(
        VERIFY_URL,
        {},
        format="json",
        **headers,
    )

    assert verify_response.status_code == 200

    # Refresh using refresh cookie
    refresh_response = csrf_client.post(
        REFRESH_URL,
        {},
        format="json",
        **headers,
    )

    assert refresh_response.status_code == 200

    assert "access" not in refresh_response.data
    assert "refresh" not in refresh_response.data

    assert "access_token" in refresh_response.cookies

    # Logout using refresh cookie
    logout_response = csrf_client.post(
        LOGOUT_URL,
        {},
        format="json",
        **headers,
    )

    assert logout_response.status_code == 200

    assert logout_response.cookies["access_token"].value == ""
    assert logout_response.cookies["refresh_token"].value == ""
    assert logout_response.cookies["csrftoken"].value == ""


@pytest.mark.django_db
def test_web_cookie_authentication_requires_csrf_for_unsafe_requests(
    csrf_client, user
):
    headers = prepare_web_client(csrf_client)

    # Login to receive authentication cookies.
    login_response = csrf_client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
        format="json",
        **headers,
    )

    assert login_response.status_code == 200

    # Safe requests do not require CSRF.
    get_response = csrf_client.get(
        PROFILE_URL,
        HTTP_X_CLIENT_TYPE="web",
    )

    assert get_response.status_code == 200

    # Unsafe requests without CSRF must be rejected.
    invalid_response = csrf_client.patch(
        PROFILE_URL,
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        format="json",
        HTTP_X_CLIENT_TYPE="web",
    )

    assert invalid_response.status_code == 403

    # The same request with a valid CSRF token must succeed.
    valid_response = csrf_client.patch(
        PROFILE_URL,
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        format="json",
        **headers,
    )

    assert valid_response.status_code == 200
    assert valid_response.data["first_name"] == "Ada"
    assert valid_response.data["last_name"] == "Lovelace"


@pytest.mark.django_db
def test_profile_requires_authentication_and_can_be_updated(
    client, authenticated_client, user
):
    assert client.get(PROFILE_URL).status_code == 401

    get_response = authenticated_client.get(PROFILE_URL)

    assert get_response.status_code == 200
    assert get_response.data["email"] == user.email

    response = authenticated_client.patch(
        PROFILE_URL,
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert response.data["first_name"] == "Ada"
    assert response.data["last_name"] == "Lovelace"

    put_response = authenticated_client.put(
        PROFILE_URL,
        {
            "first_name": "Grace",
            "last_name": "Hopper",
        },
        format="json",
    )

    assert put_response.status_code == 200
    assert put_response.data["first_name"] == "Grace"
    assert put_response.data["last_name"] == "Hopper"


@pytest.mark.django_db
def test_change_password_validates_and_updates_password(
    client, authenticated_client, user
):
    # Invalid old password
    invalid_response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": "wrong-password",
            "new_password": NEW_PASSWORD,
            "new_password1": NEW_PASSWORD,
        },
        format="json",
    )

    assert invalid_response.status_code == 400

    # Mismatched new passwords
    mismatch_response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password1": "Different#StrongPass456",
        },
        format="json",
    )

    assert mismatch_response.status_code == 400

    # Valid password change
    response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password1": NEW_PASSWORD,
        },
        format="json",
    )

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.check_password(NEW_PASSWORD)

    # The new password must work.
    login_response = client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": NEW_PASSWORD,
        },
        format="json",
    )

    assert login_response.status_code == 200


@pytest.mark.django_db
def test_password_change_revokes_all_refresh_tokens_and_old_access_token(
    user,
):
    client = APIClient()

    # Login and obtain the original access and refresh tokens.
    login_response = client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
        format="json",
    )

    assert login_response.status_code == 200

    old_access_token = login_response.data["access"]
    old_refresh_token = login_response.data["refresh"]

    # Create another outstanding refresh token for the same user.
    another_refresh_token = str(RefreshToken.for_user(user))

    # Change password using the original access token.
    password_response = client.patch(
        PASSWORD_URL,
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password1": NEW_PASSWORD,
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {old_access_token}",
    )

    assert password_response.status_code == 200

    user.refresh_from_db()

    assert user.check_password(NEW_PASSWORD)

    # All outstanding refresh tokens must be blacklisted.
    outstanding_tokens = OutstandingToken.objects.filter(user=user)

    assert outstanding_tokens.exists()

    for outstanding_token in outstanding_tokens:
        assert BlacklistedToken.objects.filter(
            token=outstanding_token
        ).exists()

    # The old refresh token must no longer work.
    old_refresh_response = client.post(
        REFRESH_URL,
        {"refresh": old_refresh_token},
        format="json",
    )

    assert old_refresh_response.status_code in (400, 401)

    another_refresh_response = client.post(
        REFRESH_URL,
        {"refresh": another_refresh_token},
        format="json",
    )

    assert another_refresh_response.status_code in (400, 401)

    # CHECK_REVOKE_TOKEN must reject the old access token.
    old_access_response = client.get(
        PROFILE_URL,
        HTTP_AUTHORIZATION=f"Bearer {old_access_token}",
    )

    assert old_access_response.status_code == 401

    # The new password must allow a fresh login.
    new_login_response = client.post(
        LOGIN_URL,
        {
            "email": user.email,
            "password": NEW_PASSWORD,
        },
        format="json",
    )

    assert new_login_response.status_code == 200


@pytest.mark.django_db
def test_delete_account_removes_user_and_profile(
    authenticated_client, user
):
    response = authenticated_client.delete(DELETE_ACCOUNT_URL)

    assert response.status_code == 204

    assert not User.objects.filter(pk=user.pk).exists()
    assert not Profile.objects.filter(user_id=user.pk).exists()
