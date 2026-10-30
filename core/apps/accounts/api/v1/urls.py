from django.urls import path
from . import views

app_name = "api-v1-accounts"

urlpatterns = [
    # Registration 
    path("register/", views.RegisterCreateAPIView.as_view(), name="register" ),

    # Custom JWT 
    path("csrf/", views.CSRFTokenAPIView.as_view(), name="csrf-token"),
    path("login/", views.CustomTokenObtainPairView.as_view(), name="jwt_login"),
    path("refresh-token/", views.CustomTokenRefreshView.as_view(), name="jwt_refresh-token"),
    path("session/verify/", views.CustomTokenVerifyView.as_view(), name="jwt_verify"),
    path("logout/", views.CustomTokenBlacklistView.as_view(), name="jwt_logout"),

    # Password management 
    path("change-password/", views.ChangePasswordGenericAPIView.as_view(), name="change_password"),

    # User profile 
    path("users/me/", views.CurrentUserProfileView.as_view(), name="user_profile"),
    path("users/me/delete-account/", views.DeleteUserDestroyAPIView.as_view(), name="delete-account"),
]
