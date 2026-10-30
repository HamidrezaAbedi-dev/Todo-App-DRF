from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from apps.accounts.api.utils.exceptions import CustomValidationException
from apps.accounts.messages import Messages
from apps.accounts.models import Profile
from apps.accounts.api.utils.image_validator import sanitize_profile_image

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Registration serializer with password checkup
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        max_length=68,
        min_length=6,
        write_only=True,
        required=True,
        style={
            "input_type": "password",
        },
    )
    password1 = serializers.CharField(
        max_length=68,
        min_length=6,
        write_only=True,
        required=True,
        style={
            "input_type": "password",
        },
    )

    class Meta:
        model = User
        fields = ["email", "password", "password1"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password1"]:
            raise serializers.ValidationError({"details": "Passwords does not match"})

        try:
            validate_password(attrs.get("password"))
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        if User.objects.filter(email=attrs.get("email")).exists():
            raise CustomValidationException(
                code="USER_ALREADY_EXISTS",
                message=Messages.user_already_exists,
            )

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data.pop("password1")
        return User.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing the authenticated user's password.
    """

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
    )
    new_password1 = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user

        if not user.check_password(attrs["old_password"]):
            raise CustomValidationException(
                code="INVALID_OLD_PASSWORD",
                message=Messages.old_password_doenst_match,
            )

        if attrs["new_password"] != attrs["new_password1"]:
            raise CustomValidationException(
                code="PASSWORD_MISMATCH",
                message=Messages.new_password_doenst_match,
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": Messages.new_password_must_be_different}
            )

        # Apply Django's configured password validators.
        validate_password(attrs["new_password"], user=user)

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating user profile information.
    """

    email = serializers.CharField(source="user.email", read_only=True)
    updated_date = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = ["id", "email", "first_name", "last_name", "image", "updated_date"]

    def validate_image(self, value):
        if value is None:
            return value

        return sanitize_profile_image(value)
