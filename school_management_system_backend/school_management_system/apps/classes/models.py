from django.db import models

from apps.core.models import TimeStampedModel


class SchoolClass(TimeStampedModel):
    """E.g. 'Grade 7', 'Form 2', 'Primary 5'."""

    name = models.CharField(max_length=50, unique=True)
    level = models.PositiveSmallIntegerField(help_text="Numeric order used for sorting classes, e.g. 1, 2, 3.")
    class_teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes_managed",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "name"]

    def __str__(self):
        return self.name


class Stream(TimeStampedModel):
    """A subdivision of a class, e.g. 'Grade 7 - Blue Stream'."""

    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="streams")
    name = models.CharField(max_length=50, help_text="e.g. 'A', 'Blue', 'East'")
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        unique_together = ("school_class", "name")
        ordering = ["school_class__level", "name"]

    def __str__(self):
        return f"{self.school_class.name} - {self.name}"
