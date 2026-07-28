from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL
    )

    action = models.CharField(
        max_length=255
    )

    model_name = models.CharField(
        max_length=100
    )

    object_id = models.CharField(
        max_length=100,
        blank=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    details = models.JSONField(
        blank=True,
        null=True
    )


    def __str__(self):
        return f"{self.action} - {self.model_name}"