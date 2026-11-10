from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def generate_index_number():
    """
    Generates a unique student index/admission number, e.g. STD00125,
    matching the format shown in the design doc (3.5.1).
    """
    last = Student.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    candidate = f"STD{next_id:05d}"
    while Student.objects.filter(index_number=candidate).exists():
        next_id += 1
        candidate = f"STD{next_id:05d}"
    return candidate


class Student(TimeStampedModel):
    """
    Student profile (3.10.2). Authenticates via `index_number` + password
    (resolved to the linked `user` by the custom auth backend).
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRANSFERRED = "transferred", "Transferred"
        GRADUATED = "graduated", "Graduated"
        SUSPENDED = "suspended", "Suspended"
        WITHDRAWN = "withdrawn", "Withdrawn"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    index_number = models.CharField(max_length=20, unique=True, db_index=True, editable=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    address = models.CharField(max_length=255, blank=True)
    admission_date = models.DateField(auto_now_add=True)
    school_class = models.ForeignKey(
        "classes.SchoolClass", on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    stream = models.ForeignKey(
        "classes.Stream", on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    photo = models.ImageField(upload_to="student_photos/", null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["index_number"]
        indexes = [models.Index(fields=["school_class", "stream"])]

    def __str__(self):
        return f"{self.index_number} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.index_number:
            # Two-step save: need a PK before we can safely compute a
            # collision-free sequential index number.
            super().save(*args, **kwargs)
            self.index_number = generate_index_number()
            kwargs["force_insert"] = False
            super().save(update_fields=["index_number"])
            return
        super().save(*args, **kwargs)


class StudentTransferHistory(TimeStampedModel):
    """Audit trail of class/stream transfers (3.10.2 'Student transfer')."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="transfer_history")
    from_class = models.ForeignKey(
        "classes.SchoolClass", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    to_class = models.ForeignKey("classes.SchoolClass", on_delete=models.SET_NULL, null=True, related_name="+")
    reason = models.CharField(max_length=255, blank=True)
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.index_number}: {self.from_class} -> {self.to_class}"
