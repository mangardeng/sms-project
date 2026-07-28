from django.db import models
from django.conf import settings

class Guardian(models.Model):
    full_name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)   # e.g. "Mother", "Guardian"
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    user_account = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="guardian_profile"
    )  # linked once the parent portal (Phase 5) is built; nullable for now

    def __str__(self):
        return self.full_name


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        GRADUATED = "GRADUATED", "Graduated"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    user_account = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="student_profile"
    )
    admission_number = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[("M", "Male"), ("F", "Female")])
    stream = models.ForeignKey("academics.Stream", on_delete=models.SET_NULL, null=True, related_name="students")
    guardians = models.ManyToManyField(Guardian, related_name="students", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    date_admitted = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"


class StudentTransferLog(models.Model):
    """Every promotion/transfer/stream-change is recorded here — this is your
    audit trail for 'Transfer student' and 'Student promotion' from the SDD."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="transfer_history")
    from_stream = models.ForeignKey("academics.Stream", on_delete=models.SET_NULL, null=True, related_name="+")
    to_stream = models.ForeignKey("academics.Stream", on_delete=models.SET_NULL, null=True, related_name="+")
    reason = models.CharField(max_length=255, blank=True)
    date = models.DateTimeField(auto_now_add=True)