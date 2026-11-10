from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.backends import UsernameOrIndexNumberBackend
from apps.accounts.permissions import IsAdmin
from apps.accounts.serializers import (
    AdminCreateUserSerializer,
    AdminResetPasswordSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    RoleTokenObtainPairSerializer,
    UserSerializer,
)
from apps.core.models import log_action

User = get_user_model()

MAX_FAILED_ATTEMPTS = 5


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: {"username": "<username OR student index number>", "password": "..."}

    A single endpoint for every user category, per design doc 3.5-3.7.
    """

    serializer_class = RoleTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("username", "")
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            self._register_failed_attempt(identifier, request)
            raise

        user = UsernameOrIndexNumberBackend._find_user(identifier)
        log_action(
            user=user,
            action="login",
            description="Successful login",
            ip_address=self._client_ip(request),
            path=request.path,
            method="POST",
        )
        return response

    def _register_failed_attempt(self, identifier, request):
        user = UsernameOrIndexNumberBackend._find_user(identifier)
        if user is None:
            return
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.is_locked = True
        user.save(update_fields=["failed_login_attempts", "is_locked"])
        log_action(
            user=user,
            action="login_failed",
            description=f"Failed login attempt #{user.failed_login_attempts}",
            ip_address=self._client_ip(request),
            path=request.path,
            method="POST",
        )

    @staticmethod
    def _client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")


class LogoutView(APIView):
    """POST /api/auth/logout/  — blacklists the refresh token so it cannot be reused."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid or already-expired token."}, status=status.HTTP_400_BAD_REQUEST)

        log_action(user=request.user, action="other", description="Logout", path=request.path, method="POST")
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — the current authenticated user's own profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """POST /api/auth/change-password/"""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    Administrator-only account management:
      create users, activate/deactivate, assign roles, reset passwords,
      per design doc 3.4.1 / 3.10.1.
    """

    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsAdmin]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]

    def get_serializer_class(self):
        if self.action == "create":
            return AdminCreateUserSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(
            user=self.request.user,
            action="create",
            model_name="User",
            object_id=user.id,
            description=f"Created account for {user.username} ({user.role})",
        )

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(
            user=self.request.user,
            action="update",
            model_name="User",
            object_id=user.id,
            description="Updated account",
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action="delete",
            model_name="User",
            object_id=instance.id,
            description=f"Deleted account {instance.username}",
        )
        instance.delete()

    def _toggle_active(self, request, pk, active):
        user = get_object_or_404(User, pk=pk)
        user.is_active = active
        user.is_locked = False if active else user.is_locked
        user.save(update_fields=["is_active", "is_locked"])
        log_action(
            user=request.user,
            action="update",
            model_name="User",
            object_id=user.id,
            description=f"{'Activated' if active else 'Deactivated'} account",
        )
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._toggle_active(request, pk, True)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._toggle_active(request, pk, False)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        target_user = get_object_or_404(User, pk=pk)
        serializer = AdminResetPasswordSerializer(data=request.data, context={"target_user": target_user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            user=request.user,
            action="update",
            model_name="User",
            object_id=target_user.id,
            description="Password reset by administrator",
        )
        return Response({"detail": "Password reset successfully. User must change it on next login."})

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        user.is_locked = False
        user.failed_login_attempts = 0
        user.save(update_fields=["is_locked", "failed_login_attempts"])
        log_action(user=request.user, action="update", model_name="User", object_id=user.id, description="Account unlocked")
        return Response(UserSerializer(user).data)
