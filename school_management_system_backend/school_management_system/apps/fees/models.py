import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class FeeStructure(TimeStampedModel):
    """Fee structure assigned to a class for a term (3.10.9)."""

    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="fee_structures")
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="fee_structures")
    name = models.CharField(max_length=150, help_text="e.g. 'Tuition Fee', 'Boarding Fee'")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_mandatory = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["school_class__level", "term"]
        unique_together = ("school_class", "term", "name")

    def __str__(self):
        return f"{self.school_class} - {self.term} - {self.name}: {self.amount}"


class Payment(TimeStampedModel):
    """A fee payment made by/for a student (3.10.9)."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"
        CHEQUE = "cheque", "Cheque"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="payments")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name="payments")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    receipt_number = models.CharField(max_length=40, unique=True, editable=False)
    payment_date = models.DateField(default=timezone.localdate)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    notes = models.CharField(max_length=255, blank=True)
    sponsor = models.ForeignKey(
        "fees.Sponsor", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments",
        help_text="Set when a sponsor (not the family) paid this amount.",
    )
    is_void = models.BooleanField(default=False, help_text="A voided payment is ignored in balances and income but kept for the record.")
    void_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"{self.receipt_number} - {self.student.index_number} - {self.amount_paid}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCPT-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


def student_balance(student, term=None) -> Decimal:
    """
    A student's outstanding fee balance.

    For one term:  fees of the student's class for that term
                   + any unpaid balance carried forward INTO that term
                   - payments made against that term (voided payments are ignored).
    For all terms: every fee - every payment (carry-forward rows are already inside it).
    """
    structures = FeeStructure.objects.filter(school_class=student.school_class)
    if term:
        structures = structures.filter(term=term)
    total_due = sum((s.amount for s in structures), Decimal("0"))

    payments = Payment.objects.filter(student=student, is_void=False)
    if term:
        payments = payments.filter(fee_structure__term=term)
    total_paid = sum((p.amount_paid for p in payments), Decimal("0"))

    carried = Decimal("0")
    if term:
        carried = sum((c.amount for c in CarryForward.objects.filter(student=student, to_term=term)), Decimal("0"))

    return total_due + carried - total_paid


class PaymentAuditLog(models.Model):
    """What an accountant changed on a payment (and why) after it was first recorded."""

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="audit_logs")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, default="edit")  # edit | void
    changes = models.TextField(blank=True, help_text="Readable list of old -> new values.")
    reason = models.CharField(max_length=255)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.payment.receipt_number} {self.action} by {self.changed_by}"


class Sponsor(TimeStampedModel):
    """An organisation or person who pays school fees for one or more students."""

    class Kind(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        ORGANIZATION = "organization", "Organization / NGO"
        CHURCH = "church", "Church / Faith group"
        GOVERNMENT = "government", "Government / Bursary"
        COMPANY = "company", "Company"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150, unique=True)
    sponsor_type = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ORGANIZATION)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Sponsorship(TimeStampedModel):
    """Records that a sponsor covers all, a percentage, or a fixed amount of a student's fees."""

    class Coverage(models.TextChoices):
        FULL = "full", "Full fees"
        PERCENTAGE = "percentage", "Percentage of fees"
        FIXED = "fixed", "Fixed amount per term"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="sponsorships")
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, related_name="sponsorships")
    coverage_type = models.CharField(max_length=12, choices=Coverage.choices, default=Coverage.FULL)
    value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Percentage (0-100) or amount per term. Not used for full sponsorship.",
    )
    academic_year = models.ForeignKey("core.AcademicYear", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                      help_text="Leave blank for every year.")
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                             help_text="Leave blank for every term.")
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["sponsor__name", "student__index_number"]

    def __str__(self):
        return f"{self.student.index_number} sponsored by {self.sponsor}"

    def covers_term(self, term) -> bool:
        if not self.is_active:
            return False
        if self.term_id and self.term_id != term.id:
            return False
        if self.academic_year_id and self.academic_year_id != term.academic_year_id:
            return False
        return True

    def share_of(self, total_due: Decimal) -> Decimal:
        if self.coverage_type == self.Coverage.FULL:
            return total_due
        if self.coverage_type == self.Coverage.PERCENTAGE:
            return (total_due * self.value / Decimal("100")).quantize(Decimal("0.01"))
        return min(self.value, total_due)


class CarryForward(TimeStampedModel):
    """Unpaid balance from one term carried into the next term's account."""

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="carry_forwards")
    from_term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="carried_out")
    to_term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="carried_in")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        unique_together = ("student", "from_term", "to_term")
        ordering = ["to_term", "student__index_number"]

    def __str__(self):
        return f"{self.student.index_number}: {self.amount} from {self.from_term} to {self.to_term}"


class Expense(TimeStampedModel):
    """Money the school spends (other than staff salaries, which have their own record)."""

    class Category(models.TextChoices):
        UTILITIES = "utilities", "Utilities (water, power, internet)"
        SUPPLIES = "supplies", "Teaching & office supplies"
        MAINTENANCE = "maintenance", "Repairs & maintenance"
        TRANSPORT = "transport", "Transport & fuel"
        FOOD = "food", "Food & catering"
        EVENTS = "events", "Events & activities"
        EQUIPMENT = "equipment", "Equipment & furniture"
        SECURITY = "security", "Security & cleaning"
        OTHER = "other", "Other"

    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_to = models.CharField(max_length=150, blank=True)
    method = models.CharField(max_length=20, choices=Payment.Method.choices, default=Payment.Method.CASH)
    reference = models.CharField(max_length=60, blank=True, help_text="Receipt / voucher number")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} {self.description}: {self.amount}"


class OtherIncome(TimeStampedModel):
    """Money received that is not a student fee (donations, grants, fundraising...)."""

    class Category(models.TextChoices):
        DONATION = "donation", "Donation"
        GRANT = "grant", "Grant"
        FUNDRAISING = "fundraising", "Fundraising"
        SALES = "sales", "Uniform / book sales"
        RENT = "rent", "Rent / hire of facilities"
        OTHER = "other", "Other"

    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_from = models.CharField(max_length=150, blank=True)
    method = models.CharField(max_length=20, choices=Payment.Method.choices, default=Payment.Method.CASH)
    reference = models.CharField(max_length=60, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "Other income"

    def __str__(self):
        return f"{self.date} {self.description}: {self.amount}"


class StaffSalary(TimeStampedModel):
    """One staff member's pay for one month."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salaries")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(help_text="1-12")
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=Decimal("0"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_date = models.DateField(null=True, blank=True)
    method = models.CharField(max_length=20, choices=Payment.Method.choices, default=Payment.Method.BANK_TRANSFER)
    reference = models.CharField(max_length=60, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        unique_together = ("staff", "year", "month")
        ordering = ["-year", "-month", "staff__last_name"]

    def __str__(self):
        return f"{self.staff} {self.year}-{self.month:02d}: {self.net_salary}"

    def save(self, *args, **kwargs):
        self.net_salary = (self.basic_salary or 0) + (self.allowances or 0) - (self.deductions or 0)
        if self.status == self.Status.PAID and not self.paid_date:
            self.paid_date = timezone.localdate()
        super().save(*args, **kwargs)
