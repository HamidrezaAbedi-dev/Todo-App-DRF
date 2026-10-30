from django.urls import path, include
from . import views

app_name = "accounts"

urlpatterns = [
    # api based authentication
    path("api/v1/", include("apps.accounts.api.v1.urls")),

    # Template based authentication
    path("registration/", views.RegistrationTemplateView.as_view(), name="registration"),
    path("login/", views.LoginTemplateView.as_view(), name="login"),
    path("change-password/", views.ChangePasswordTemplateView.as_view(), name="change-password"),
    path("user-profile/", views.CurrentUserProfileTemplateView.as_view(), name="user-profile"),
]