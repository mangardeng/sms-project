from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

DEFAULT_LOAN_DAYS = 14
FINE_PER_DAY = Decimal("0.50")


class Book(TimeStampedModel):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.available_copies}/{self.total_copies} available)"


class BorrowingRecord(TimeStampedModel):
    """Issue/return record for a book (3.10.10)."""

    class Status(models.TextChoices):
        BORROWED = "borrowed", "Borrowed"
        RETURNED = "returned", "Returned"
        OVERDUE = "overdue", "Overdue"
        LOST = "lost", "Lost"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowing_records")
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="borrowing_records", null=True, blank=True
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", on_delete=models.CASCADE, related_name="borrowing_records", null=True, blank=True
    )
    issued_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BORROWED)
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-issued_date"]

    def __str__(self):
        borrower = self.student or self.teacher
        return f"{self.book.title} -> {borrower} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = timezone.now().date() + timedelta(days=DEFAULT_LOAN_DAYS)
        super().save(*args, **kwargs)

    def calculate_fine(self) -> Decimal:
        end_date = self.returned_date or timezone.now().date()
        overdue_days = (end_date - self.due_date).days
        if overdue_days > 0:
            return FINE_PER_DAY * overdue_days
        return Decimal("0.00")

    def mark_returned(self):
        self.returned_date = timezone.now().date()
        self.fine_amount = self.calculate_fine()
        self.status = "returned"
        self.save(update_fields=["returned_date", "fine_amount", "status"])
        self.book.available_copies = models.F("available_copies") + 1
        self.book.save(update_fields=["available_copies"])
