from django.views.generic import TemplateView


class RegistrationTemplateView(TemplateView):
    template_name = "accounts/register.html"

class LoginTemplateView(TemplateView):
    template_name = "accounts/login.html"

class ChangePasswordTemplateView(TemplateView):
    template_name = "accounts/change_password.html"

class CurrentUserProfileTemplateView(TemplateView):
    template_name = "accounts/user_profile.html"
