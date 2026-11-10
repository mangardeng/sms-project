from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

USER_EDITABLE_FIELDS = ("first_name", "last_name", "email", "phone_number")


class UserFieldsUpdateMixin(serializers.Serializer):
    """
    Lets a profile serializer (Student / Teacher / Parent) edit the
    linked User's name, email and phone number in the same PATCH, so the
    frontend edit forms can expose the same fields the Django admin does.
    Must be listed BEFORE ModelSerializer in the class bases.
    """

    first_name = serializers.CharField(write_only=True, required=False, max_length=150)
    last_name = serializers.CharField(write_only=True, required=False, max_length=150)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)

    def update(self, instance, validated_data):
        user_data = {k: validated_data.pop(k) for k in USER_EDITABLE_FIELDS if k in validated_data}
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if user_data:
                user = instance.user
                for key, value in user_data.items():
                    setattr(user, key, value)
                user.save(update_fields=list(user_data))
        return instance


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends SimpleJWT's login serializer so that:
      * the `username` field accepts either an actual username OR a
        student index/admission number (resolved by
        apps.accounts.backends.UsernameOrIndexNumberBackend),
      * the returned tokens embed the user's role,
      * the response body also returns basic profile info + the
        frontend dashboard route, per design doc 3.6/3.7 ("the backend
        returns the authenticated user's basic information and
        permissions").
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name()
        token["must_change_password"] = user.must_change_password
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Reset failed-login counters on success.
        if user.failed_login_attempts:
            user.failed_login_attempts = 0
            user.save(update_fields=["failed_login_attempts"])

        data["user"] = UserSerializer(user).data
        data["dashboard"] = user.dashboard_path
        return data


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "first_name", "last_name", "email",
            "phone_number", "role", "role_display", "is_active",
            "must_change_password", "date_joined", "last_login",
        )
        read_only_fields = ("id", "date_joined", "last_login")


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """
    Used by administrators to create accounts for staff-type users
    (head teacher, registrar, teacher, accountant, librarian). Student
    and Parent accounts are usually created implicitly via the
    students/parents apps (registration flows) but can also be created
    here directly by an admin.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            "id", "username", "first_name", "last_name", "email",
            "phone_number", "role", "password",
        )

    def validate_role(self, value):
        if value == User.Role.STUDENT:
            raise serializers.ValidationError(
                "Student accounts must be created through the Student registration endpoint "
                "so an index number is generated."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.must_change_password = True
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user


class AdminResetPasswordSerializer(serializers.Serializer):
    """Admin-initiated password reset for another user's account."""

    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def save(self, **kwargs):
        target_user = self.context["target_user"]
        target_user.set_password(self.validated_data["new_password"])
        target_user.must_change_password = True
        target_user.save(update_fields=["password", "must_change_password"])
        return target_user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
