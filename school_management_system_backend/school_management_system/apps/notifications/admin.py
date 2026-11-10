from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "channel", "recipient", "broadcast_role", "is_broadcast", "is_read", "created_at")
    list_filter = ("category", "channel", "is_broadcast", "is_read")
    search_fields = ("title", "message")
