from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import has_role
from apps.core.models import log_action
from apps.notifications.models import Notification
from apps.notifications.serializers import BroadcastNotificationSerializer, NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Every user sees only their own notifications (personal or broadcast
    to their role). Sending a targeted notification directly to one
    user is limited to staff roles; broadcasting to a whole role/school
    is limited to Admin/Head Teacher via the `broadcast` action.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["category", "is_read"]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(recipient=user).select_related("created_by")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_superuser or has_role(
            user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.TEACHER,
            User.Role.REGISTRAR, User.Role.ACCOUNTANT, User.Role.LIBRARIAN,
        )):
            raise PermissionDenied("You are not allowed to send notifications.")
        instance = serializer.save(created_by=user)
        log_action(user=user, action="create", model_name="Notification", object_id=instance.id)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        from django.utils import timezone

        updated = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"marked_read": updated})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread_count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=False, methods=["post"])
    def broadcast(self, request):
        """POST /api/notifications/broadcast/ — Admin/Head Teacher announcement to a role or the whole school."""
        user = request.user
        if not (user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER)):
            raise PermissionDenied("Only an administrator or head teacher may broadcast announcements.")

        serializer = BroadcastNotificationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        notifications = serializer.save()
        log_action(
            user=user, action="create", model_name="Notification",
            description=f"Broadcast '{request.data.get('title')}' to {len(notifications)} users",
        )
        return Response({"detail": f"Notification sent to {len(notifications)} users."})
