from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.notifications.models import Notification

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = (
            "id", "recipient", "broadcast_role", "is_broadcast", "category", "channel",
            "title", "message", "is_read", "read_at", "created_by", "created_by_name", "created_at",
        )
        read_only_fields = ("is_read", "read_at", "created_by", "created_at")


class BroadcastNotificationSerializer(serializers.Serializer):
    """
    POST payload for sending one announcement to every user of a given
    role (or to every active user if role is omitted) — 3.10.11
    'School announcements'.
    """

    role = serializers.ChoiceField(choices=User.Role.choices, required=False, allow_null=True)
    category = serializers.ChoiceField(choices=Notification.Category.choices, default=Notification.Category.ANNOUNCEMENT)
    channel = serializers.ChoiceField(choices=Notification.Channel.choices, default=Notification.Channel.IN_APP)
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context["request"]
        role = self.validated_data.get("role")

        recipients = User.objects.filter(is_active=True)
        if role:
            recipients = recipients.filter(role=role)

        notifications = [
            Notification(
                recipient=user,
                category=self.validated_data["category"],
                channel=self.validated_data["channel"],
                title=self.validated_data["title"],
                message=self.validated_data["message"],
                broadcast_role=role or "",
                is_broadcast=True,
                created_by=request.user,
            )
            for user in recipients
        ]
        Notification.objects.bulk_create(notifications)
        return notifications
