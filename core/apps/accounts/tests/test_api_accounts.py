import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

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


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="member@example.com",
        password="Strong#TodoPass123",
    )


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


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
    assert not User.objects.filter(email="invalid@example.com").exists()


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
    login_response = client.post(
        LOGIN_URL,
        {"email": user.email, "password": "Strong#TodoPass123"},
        format="json",
    )

    assert login_response.status_code == 200
    access_token = login_response.data["access"]
    refresh_token = login_response.data["refresh"]

    verify_response = client.post(
        VERIFY_URL,
        {"token": access_token},
        format="json",
    )
    assert verify_response.status_code == 200
    assert verify_response.data == {"detail": "Token is valid."}

    refresh_response = client.post(
        REFRESH_URL,
        {"refresh": refresh_token},
        format="json",
    )
    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data

    logout_response = client.post(
        LOGOUT_URL,
        {"refresh": refresh_token},
        format="json",
    )
    assert logout_response.status_code == 200

    invalid_refresh_response = client.post(
        REFRESH_URL,
        {"refresh": refresh_token},
        format="json",
    )
    assert invalid_refresh_response.status_code in (400, 401)


@pytest.mark.django_db
def test_login_rejects_invalid_credentials(client, user):
    response = client.post(
        LOGIN_URL,
        {"email": user.email, "password": "incorrect-password"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_web_authentication_uses_http_only_cookies(client, user):
    headers = {"HTTP_X_CLIENT_TYPE": "web"}
    login_response = client.post(
        LOGIN_URL,
        {"email": user.email, "password": "Strong#TodoPass123"},
        format="json",
        **headers,
    )

    assert login_response.status_code == 200
    assert "access" not in login_response.data
    assert "refresh" not in login_response.data
    assert login_response.cookies["access_token"]["httponly"]
    assert login_response.cookies["refresh_token"]["httponly"]

    verify_response = client.post(
        VERIFY_URL,
        {},
        format="json",
        **headers,
    )
    assert verify_response.status_code == 200

    refresh_response = client.post(
        REFRESH_URL,
        {},
        format="json",
        **headers,
    )
    assert refresh_response.status_code == 200
    assert "access" not in refresh_response.data
    assert "access_token" in refresh_response.cookies

    logout_response = client.post(
        LOGOUT_URL,
        {},
        format="json",
        **headers,
    )
    assert logout_response.status_code == 200
    assert logout_response.cookies["access_token"].value == ""
    assert logout_response.cookies["refresh_token"].value == ""


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
        {"first_name": "Ada", "last_name": "Lovelace"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert response.data["first_name"] == "Ada"
    assert response.data["last_name"] == "Lovelace"

    put_response = authenticated_client.put(
        PROFILE_URL,
        {"first_name": "Grace", "last_name": "Hopper"},
        format="json",
    )
    assert put_response.status_code == 200
    assert put_response.data["first_name"] == "Grace"
    assert put_response.data["last_name"] == "Hopper"


@pytest.mark.django_db
def test_change_password_validates_and_updates_password(
    client, authenticated_client, user
):
    invalid_response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": "wrong-password",
            "new_password": "Another#StrongPass456",
            "new_password1": "Another#StrongPass456",
        },
        format="json",
    )
    assert invalid_response.status_code == 400

    mismatch_response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": "Strong#TodoPass123",
            "new_password": "Another#StrongPass456",
            "new_password1": "Different#StrongPass456",
        },
        format="json",
    )
    assert mismatch_response.status_code == 400

    response = authenticated_client.patch(
        PASSWORD_URL,
        {
            "old_password": "Strong#TodoPass123",
            "new_password": "Another#StrongPass456",
            "new_password1": "Another#StrongPass456",
        },
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("Another#StrongPass456")

    login_response = client.post(
        LOGIN_URL,
        {"email": user.email, "password": "Another#StrongPass456"},
        format="json",
    )
    assert login_response.status_code == 200


@pytest.mark.django_db
def test_delete_account_removes_user_and_profile(
    authenticated_client, user
):
    response = authenticated_client.delete(DELETE_ACCOUNT_URL)

    assert response.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    assert not Profile.objects.filter(pk=user.pk).exists()
