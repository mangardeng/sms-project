from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Teacher(TimeStampedModel):
    """Extends the base User with teacher-specific fields (3.10.3)."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    staff_id = models.CharField(max_length=20, unique=True, help_text="e.g. TCH0001")
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_employed = models.DateField(null=True, blank=True)
    qualification = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="teacher_photos/", null=True, blank=True)
    is_active_staff = models.BooleanField(default=True)

    class Meta:
        ordering = ["staff_id"]

    def __str__(self):
        return f"{self.staff_id} - {self.user.get_full_name()}"

    @property
    def assigned_classes(self):
        """Classes this teacher currently teaches at least one subject in."""
        from apps.subjects.models import ClassSubject

        class_ids = ClassSubject.objects.filter(teacher=self).values_list("school_class_id", flat=True).distinct()
        from apps.classes.models import SchoolClass

        return SchoolClass.objects.filter(id__in=class_ids)
