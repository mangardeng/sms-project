from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Parent(TimeStampedModel):
    """Parent/guardian profile (3.10.4)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_profile")
    address = models.CharField(max_length=255, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    alternate_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.user.get_full_name()} (Parent)"


class ParentStudent(TimeStampedModel):
    """
    THE critical access-control relationship (design doc 3.13/3.14/4.9).

    The backend must verify this relationship exists before returning
    ANY information about a student to a parent. It must never rely on
    the frontend to hide/show data — every API view touching student
    data must check this table for the requesting parent.
    """

    class Relationship(models.TextChoices):
        FATHER = "father", "Father"
        MOTHER = "mother", "Mother"
        GUARDIAN = "guardian", "Guardian"
        OTHER = "other", "Other"

    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="student_links")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="parent_links")
    relationship = models.CharField(max_length=20, choices=Relationship.choices, default=Relationship.GUARDIAN)
    is_primary_contact = models.BooleanField(default=True)

    class Meta:
        unique_together = ("parent", "student")
        ordering = ["-is_primary_contact"]

    def __str__(self):
        return f"{self.parent} -> {self.student} ({self.relationship})"
