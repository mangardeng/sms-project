from django.contrib import admin

from apps.fees.models import FeeStructure, Payment


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("name", "school_class", "term", "amount", "is_mandatory")
    list_filter = ("term", "is_mandatory")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "student", "amount_paid", "method", "payment_date")
    search_fields = ("receipt_number", "student__index_number")


from apps.fees.models import (  # noqa: E402
    CarryForward,
    Expense,
    OtherIncome,
    PaymentAuditLog,
    Sponsor,
    Sponsorship,
    StaffSalary,
)

for model in (Sponsor, Sponsorship, CarryForward, Expense, OtherIncome, StaffSalary, PaymentAuditLog):
    admin.site.register(model)
