from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Attendance(TimeStampedModel):
    """
    Daily attendance record (3.10.7). One record per student per date.
    Teachers should only record attendance for classes assigned to them
    (3.4.4) — enforced in apps.attendance.permissions, not just here.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance_records")
    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    remarks = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="attendance_recorded")

    class Meta:
        unique_together = ("student", "date")
        ordering = ["-date"]
        indexes = [models.Index(fields=["school_class", "date"])]

    def __str__(self):
        return f"{self.student.index_number} | {self.date} | {self.status}"
