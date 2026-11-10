from django.db import models

from apps.core.models import TimeStampedModel


class Subject(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_compulsory = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassSubject(TimeStampedModel):
    """
    Assigns a Subject to a SchoolClass and (optionally) a Teacher.
    This is the join table that answers "which classes/subjects is this
    teacher assigned to?", which is what enforces the rule that a
    "teacher must not modify students or classes outside the teacher's
    assigned responsibilities" (3.4.4).
    """

    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_subjects")
    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subject_assignments",
    )
    academic_year = models.ForeignKey("core.AcademicYear", on_delete=models.CASCADE, related_name="class_subjects")

    class Meta:
        unique_together = ("school_class", "subject", "academic_year")
        ordering = ["school_class__level", "subject__name"]

    def __str__(self):
        teacher_name = self.teacher.user.get_full_name() if self.teacher else "Unassigned"
        return f"{self.school_class} | {self.subject.code} | {teacher_name}"
