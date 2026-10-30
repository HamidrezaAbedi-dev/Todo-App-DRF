from rest_framework.generics import (
    CreateAPIView, GenericAPIView, RetrieveUpdateAPIView,
)
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,TokenRefreshView,TokenVerifyView,TokenBlacklistView,
)
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from .serializers import RegisterSerializer, ChangePasswordSerializer, ProfileSerializer
from apps.accounts.messages import Messages
from apps.accounts.api.utils.jwt_sessions import blacklist_refresh_token, blacklist_all_user_refresh_tokens
from apps.accounts.api.utils.jwt_cookies import (
    set_jwt_cookie, delete_jwt_cookie, is_web_client, get_access_cookie_name, get_refresh_cookie_name
)
from apps.accounts.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterCreateAPIView(CreateAPIView):
    serializer_class = RegisterSerializer
    queryset = User.objects.all()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login:
    - Web: set HttpOnly cookies and omit tokens from JSON.
    - App: return tokens in the default Simple JWT JSON response.
    """

    def post(self, request: Request, *args, **kwargs,) -> Response:
        response = super().post(request, *args, **kwargs)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Independent apps receive the default JSON response.
        if not is_web_client(request):
            return response

        access_token = response.data.get("access")
        refresh_token = response.data.get("refresh")

        if access_token:
            set_jwt_cookie(
                response,
                key=get_access_cookie_name(),
                value=access_token,
                lifetime=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
            )

        if refresh_token:
            set_jwt_cookie(
                response,
                key=get_refresh_cookie_name(),
                value=refresh_token,
                lifetime=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
            )

        # For web clients, tokens are delivered only through cookies.
        response.data.pop("access", None)
        response.data.pop("refresh", None)

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh:
    - Web: read the refresh token from its cookie, rotate cookies
        when configured, and omit tokens from JSON.
    - App: accept refresh in JSON and return the default JSON response.
    """

    def post(self, request: Request, *args, **kwargs,) -> Response:
        web_client = is_web_client(request)
        data = request.data.copy()

        if web_client:
            refresh_token = request.COOKIES.get(
                get_refresh_cookie_name()
            )

            if not refresh_token:
                return Response(
                    {"detail": "Refresh token cookie is missing."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # For browser clients, use the cookie as the token source.
            data["refresh"] = refresh_token

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {"detail": "Refresh token is invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_data = dict(serializer.validated_data)

        response = Response(
            token_data,
            status=status.HTTP_200_OK,
        )

        # Apps keep the standard JSON behavior.
        if not web_client:
            return response

        access_token = token_data.get("access")
        new_refresh_token = token_data.get("refresh")

        if access_token:
            set_jwt_cookie(
                response,
                key=get_access_cookie_name(),
                value=access_token,
                lifetime=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
            )

        # A replacement refresh token is returned when rotation is enabled.
        if new_refresh_token:
            set_jwt_cookie(
                response,
                key=get_refresh_cookie_name(),
                value=new_refresh_token,
                lifetime=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
            )

        # Browser clients receive tokens through HttpOnly cookies only.
        response.data.pop("access", None)
        response.data.pop("refresh", None)

        return response


class CustomTokenVerifyView(TokenVerifyView):
    """
    Verify:
    - Web: read the token from the access cookie.
    - App: read the token from the JSON body.
    """

    def post(
        self,
        request: Request,
        *args,
        **kwargs,
    ) -> Response:
        data = request.data.copy()

        if is_web_client(request):
            access_token = request.COOKIES.get(
                get_access_cookie_name()
            )

            if not access_token:
                return Response(
                    {"detail": "Access token cookie is missing."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            data["token"] = access_token

        serializer = self.get_serializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {"detail": "Token is invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"detail": "Token is valid."}, status=status.HTTP_200_OK)


class CustomTokenBlacklistView(TokenBlacklistView):
    """
    Logout:
    - Web: blacklist the refresh cookie and clear authentication cookies.
    - App: blacklist the refresh token supplied in JSON.
    """

    def post(self, request: Request, *args, **kwargs,) -> Response:
        web_client = is_web_client(request)

        if web_client:
            refresh_token = request.COOKIES.get(
                get_refresh_cookie_name()
            )
        else:
            refresh_token = request.data.get("refresh")

        if not refresh_token:
            response = Response(
                {"detail": "Refresh token is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

            if web_client:
                self._clear_auth_cookies(response)

            return response

        revoked = blacklist_refresh_token(refresh_token)

        if not revoked:
            response = Response(
                {
                    "detail": (
                        "Refresh token is invalid or "
                        "could not be revoked."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

            if web_client:
                self._clear_auth_cookies(response)

            return response

        response = Response(status=status.HTTP_200_OK)

        if web_client:
            self._clear_auth_cookies(response)

        return response

    @staticmethod
    def _clear_auth_cookies(response: Response) -> None:
        delete_jwt_cookie(
            response,
            get_access_cookie_name(),
        )

        delete_jwt_cookie(
            response,
            get_refresh_cookie_name(),
        )

        # Delete the CSRF cookie using Django's configured settings.
        response.delete_cookie(
            key=settings.CSRF_COOKIE_NAME,
            path=settings.CSRF_COOKIE_PATH,
            domain=settings.CSRF_COOKIE_DOMAIN,
            samesite=settings.CSRF_COOKIE_SAMESITE,
        )


class ChangePasswordGenericAPIView(GenericAPIView):
    """
    Change the authenticated user's password.

    - Web: read the refresh token from the cookie, revoke it,
        and clear authentication cookies.
    - App: optionally revoke the refresh token supplied in JSON.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def patch(self, request: Request, *args, **kwargs,) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        web_client = is_web_client(request)

        if web_client:
            refresh_token = request.COOKIES.get(
                get_refresh_cookie_name()
            )
        else:
            refresh_token = request.data.get("refresh")

        # Change the password of the authenticated user only.
        serializer.save()

        # Revoke the previous refresh token if provided.
        if refresh_token:
            revoked = blacklist_refresh_token(refresh_token)

            if not revoked:
                # Password has already changed.
                # Log this event if your project has a logger configured.
                pass

        response = Response(
            {
                "detail": Messages.password_changed_successfully,
            },
            status=status.HTTP_200_OK,
        )

        if web_client:
            CustomTokenBlacklistView._clear_auth_cookies(response)

        return response


class CurrentUserProfileView(RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's profile.
    """
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, user=self.request.user)
        return obj



class DeleteUserDestroyAPIView(APIView):
    """
    Delete the authenticated user's account.

    - Revoke the current refresh token when provided.
    - Revoke all outstanding refresh tokens associated with the user.
    - Delete the user and related objects.
    - Clear authentication cookies for web clients.
    """

    permission_classes = (IsAuthenticated,)

    def delete(
        self,
        request: Request,
        *args,
        **kwargs,
    ) -> Response:
        user = request.user
        web_client = is_web_client(request)

        # Get the current refresh token using the same logic as logout.
        if web_client:
            refresh_token = request.COOKIES.get(
                get_refresh_cookie_name()
            )
        else:
            refresh_token = request.data.get("refresh")

        with transaction.atomic():
            # Revoke the current refresh token directly.
            if refresh_token:
                blacklist_refresh_token(refresh_token)

            # Revoke all other outstanding refresh tokens for this user.
            blacklist_all_user_refresh_tokens(user)

            # Delete the account and related Profile via CASCADE.
            user.delete()

        response = Response(
            status=status.HTTP_204_NO_CONTENT,
        )

        if web_client:
            CustomTokenBlacklistView._clear_auth_cookies(response)

        return response
