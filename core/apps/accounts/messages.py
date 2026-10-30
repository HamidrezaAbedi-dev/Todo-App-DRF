from django.utils.translation import gettext as _


class Messages:

    email_missing = _("email is missing")
    password_missing = _("password missing")
    invalid_credentials = _("authentication failed please check your inputs")
    authenticated_successfully = _("you have successfully logged in")
    registered_successfully = _("your registration was successful")

    jwt_missing = _("token field cannot be empty")
    jwt_expired = _("token has been expired")
    jwt_invalid = _("invalid token")

    password_changed_successfully = _("Password updated successfully")
    password_reset_completed = _("Password reset successfully")
    password_reset_link_sent = _("We have sent you a link to reset your password")
    user_already_exists = _("User already exists")
    user_not_found = _("user not found")

    old_password_doenst_match = _("Old password doesnt match")
    new_password_doenst_match = _("New passwords doesnt match")
    new_password_must_be_different = _(
        "The new password must be different from the current password."
    )
    token_refreshed_successfully = _("Token refreshed successfully.")
    logout_successfully = _("Logged out successfully")
