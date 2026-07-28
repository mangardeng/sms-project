from django.db import models
from django.conf import settings

from students.models import Student
from teachers.models import Teacher
from academics.models import SchoolClass


class StudentAttendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        EXCUSED = "EXCUSED", "Excused"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("student", "date")
        ordering = ["-date", "student"]

    def __str__(self):
        return f"{self.student} - {self.date} ({self.status})"


class TeacherAttendance(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    status = models.CharField(
        max_length=10,
        choices=StudentAttendance.Status.choices,
        default=StudentAttendance.Status.PRESENT
    )

    class Meta:
        unique_together = ("teacher", "date")
        ordering = ["-date", "teacher"]

    def __str__(self):
        return f"{self.teacher} - {self.date} ({self.status})"