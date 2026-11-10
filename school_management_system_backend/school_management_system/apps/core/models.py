from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model providing created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AcademicYear(TimeStampedModel):
    """E.g. 2025/2026 academic year."""

    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2025/2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one academic year is marked current at a time.
        if self.is_current:
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Term(TimeStampedModel):
    """A term/semester within an academic year."""

    class TermName(models.TextChoices):
        TERM_1 = "term_1", "Term 1"
        TERM_2 = "term_2", "Term 2"
        TERM_3 = "term_3", "Term 3"

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=20, choices=TermName.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ("academic_year", "name")
        ordering = ["academic_year__start_date", "start_date"]

    def __str__(self):
        return f"{self.get_name_display()} - {self.academic_year.name}"

    def save(self, *args, **kwargs):
        if self.is_current:
            Term.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """
    Generic audit trail. Used for security-sensitive actions such as
    examination mark changes, account activation/deactivation, and
    unauthorized access attempts (e.g. a parent requesting a student
    they are not linked to).
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Login Failed"
        ACCESS_DENIED = "access_denied", "Access Denied"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {self.user} | {self.action} | {self.model_name}"


def log_action(*, user=None, action, model_name="", object_id="", description="",
               ip_address=None, path="", method=""):
    """Convenience helper to write an AuditLog entry from anywhere in the codebase."""
    return AuditLog.objects.create(
        user=user if (user and getattr(user, "is_authenticated", False)) else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        description=description,
        ip_address=ip_address,
        path=path,
        method=method,
    )
