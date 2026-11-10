from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    In-system notification (3.10.11). Email/SMS delivery can be wired
    in later via a signal or background task (Celery) without changing
    this model — `channel` records how it was (or should be) delivered.
    """

    class Category(models.TextChoices):
        ANNOUNCEMENT = "announcement", "School Announcement"
        EXAM_RESULT = "exam_result", "Examination Result"
        FEE_REMINDER = "fee_reminder", "Fee Reminder"
        ATTENDANCE_ALERT = "attendance_alert", "Attendance Alert"
        LIBRARY = "library", "Library"
        GENERAL = "general", "General"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications",
        help_text="Null recipient + is_broadcast=True means it targets a whole role or the entire school.",
        null=True, blank=True,
    )
    broadcast_role = models.CharField(
        max_length=20, blank=True,
        help_text="If set (e.g. 'parent', 'teacher'), this is a broadcast to everyone with that role.",
    )
    is_broadcast = models.BooleanField(default=False)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="notifications_sent"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        target = self.recipient or f"role:{self.broadcast_role}" or "everyone"
        return f"[{self.category}] {self.title} -> {target}"

    def mark_read(self):
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
