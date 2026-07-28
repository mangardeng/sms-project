from django.db import models
from django.conf import settings

class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    employee_id = models.CharField(max_length=30, unique=True)
    date_joined = models.DateField()
    subjects_qualified = models.CharField(max_length=255, blank=True)  # comma-separated for now; normalize in Phase 3 exams module if needed

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class SubjectAllocation(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="allocations")
    school_class = models.ForeignKey("academics.SchoolClass", on_delete=models.CASCADE)
    stream = models.ForeignKey("academics.Stream", on_delete=models.CASCADE, null=True, blank=True)
    subject_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("teacher", "school_class", "stream", "subject_name")

    def __str__(self):
        return f"{self.teacher} → {self.subject_name} ({self.school_class})"