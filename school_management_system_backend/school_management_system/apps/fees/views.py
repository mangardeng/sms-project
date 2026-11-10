from datetime import date

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import has_role
from apps.core.models import Term, log_action
from apps.fees.models import (
    CarryForward,
    Expense,
    FeeStructure,
    OtherIncome,
    Payment,
    PaymentAuditLog,
    Sponsor,
    Sponsorship,
    StaffSalary,
)
from apps.fees.permissions import FeeAccessPermission, FinanceAccessPermission, is_accountant
from apps.fees.serializers import (
    CarryForwardSerializer,
    ExpenseSerializer,
    FeeStructureSerializer,
    OtherIncomeSerializer,
    PaymentAuditLogSerializer,
    PaymentSerializer,
    SponsorSerializer,
    SponsorshipSerializer,
    StaffSalarySerializer,
    StudentFeeBalanceSerializer,
)
from apps.fees.services import (
    arrears_for_term,
    finance_summary,
    generate_carry_forward,
    generate_payroll,
    sponsorship_report,
    STAFF_ROLES,
)
from apps.parents.services import get_linked_student_ids, parent_owns_student
from apps.students.models import Student


class FeeStructureViewSet(viewsets.ModelViewSet):
    serializer_class = FeeStructureSerializer
    filterset_fields = ["school_class", "term"]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [FeeAccessPermission()]

    def get_queryset(self):
        return FeeStructure.objects.select_related("school_class", "term")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="FeeStructure", object_id=instance.id)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Recording a payment: administrator or accountant.
    Correcting or voiding a payment: the accountant only. Every correction needs a reason and is
    kept in the payment's audit trail. Payments are never deleted.
    """

    permission_classes = [FeeAccessPermission]
    serializer_class = PaymentSerializer
    filterset_fields = ["student", "fee_structure", "method", "sponsor", "is_void"]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("student__user", "fee_structure", "sponsor")

        if user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return qs
        if user.role == User.Role.PARENT:
            return qs.filter(student_id__in=get_linked_student_ids(user), is_void=False)
        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            return qs.filter(student=user.student_profile, is_void=False)
        return qs.none()

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        log_action(
            user=self.request.user, action="create", model_name="Payment", object_id=instance.id,
            description=f"Recorded payment {instance.receipt_number} for student {instance.student_id}",
        )

    @staticmethod
    def _describe(payment):
        return {
            "student": f"{payment.student.index_number}",
            "fee": payment.fee_structure.name,
            "amount": str(payment.amount_paid),
            "method": payment.get_method_display(),
            "date": str(payment.payment_date),
            "sponsor": payment.sponsor.name if payment.sponsor_id else "",
            "notes": payment.notes,
        }

    def perform_update(self, serializer):
        user = self.request.user
        if not is_accountant(user):
            raise PermissionDenied("Only the accountant can correct a recorded payment.")
        payment = serializer.instance
        if payment.is_void:
            raise ValidationError({"detail": "This payment was voided and can no longer be edited."})
        reason = str(self.request.data.get("reason", "")).strip()
        if not reason:
            raise ValidationError({"reason": "Give a short reason for the correction."})

        before = self._describe(payment)
        payment = serializer.save()
        payment.refresh_from_db()
        after = self._describe(payment)
        changes = "; ".join(f"{k}: {before[k] or '-'} -> {after[k] or '-'}" for k in before if before[k] != after[k])
        if changes:
            PaymentAuditLog.objects.create(payment=payment, changed_by=user, action="edit", changes=changes, reason=reason)
            log_action(user=user, action="update", model_name="Payment", object_id=payment.id, description=f"Corrected {payment.receipt_number}: {changes}. Reason: {reason}")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Payments are never deleted. If one was recorded by mistake, ask the accountant to void it.")

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """POST /api/fees/payments/{id}/void/ {reason} - accountant cancels a payment entered by mistake."""
        if not is_accountant(request.user):
            raise PermissionDenied("Only the accountant can void a payment.")
        payment = self.get_object()
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            raise ValidationError({"reason": "Give a reason for voiding this payment."})
        if payment.is_void:
            raise ValidationError({"detail": "This payment is already void."})
        payment.is_void = True
        payment.void_reason = reason[:255]
        payment.save(update_fields=["is_void", "void_reason", "updated_at"])
        PaymentAuditLog.objects.create(
            payment=payment, changed_by=request.user, action="void",
            changes=f"voided {payment.amount_paid}", reason=reason[:255],
        )
        log_action(user=request.user, action="update", model_name="Payment", object_id=payment.id, description=f"Voided {payment.receipt_number}. Reason: {reason}")
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """GET /api/fees/payments/{id}/history/ - the correction trail of one payment (staff only)."""
        if not (request.user.is_superuser or has_role(request.user, User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.HEAD_TEACHER)):
            raise PermissionDenied("Only finance staff can see a payment's history.")
        payment = self.get_object()
        return Response(PaymentAuditLogSerializer(payment.audit_logs.select_related("changed_by"), many=True).data)


class FeeBalanceView(viewsets.ViewSet):
    """
    GET /api/fees/balance/?student=<id>&term=<id>
    Convenience endpoint computing a single student's outstanding balance,
    enforcing the same parent/student ownership rule as everywhere else.
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        student_id = request.query_params.get("student")
        term_id = request.query_params.get("term")

        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            student = user.student_profile
        elif student_id:
            student = Student.objects.filter(pk=student_id).first()
            if student is None:
                raise NotFound("Student not found.")
            if user.role == User.Role.PARENT and not parent_owns_student(user, student.id):
                raise PermissionDenied("You are not linked to this student.")
            if user.role not in (User.Role.PARENT,) and not (
                user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.HEAD_TEACHER, User.Role.REGISTRAR)
            ):
                raise PermissionDenied("You do not have access to this student's fee balance.")
        else:
            raise NotFound("Provide a student id.")

        term = Term.objects.filter(pk=term_id).first() if term_id else None
        return Response(StudentFeeBalanceSerializer.build(student, term=term))


# ---------------------------------------------------------------------------
# Finance: sponsorship, carry-forward, expenses, other income, salaries, summary
# ---------------------------------------------------------------------------
class SponsorViewSet(viewsets.ModelViewSet):
    permission_classes = [FinanceAccessPermission]
    serializer_class = SponsorSerializer
    queryset = Sponsor.objects.all()
    filterset_fields = ["is_active", "sponsor_type"]
    search_fields = ["name", "contact_person"]


class SponsorshipViewSet(viewsets.ModelViewSet):
    """Which students are under sponsorship, by whom, and how much of their fees the sponsor covers."""

    permission_classes = [FinanceAccessPermission]
    serializer_class = SponsorshipSerializer
    filterset_fields = ["student", "sponsor", "is_active", "term", "academic_year"]
    search_fields = ["student__index_number", "student__user__first_name", "student__user__last_name", "sponsor__name"]

    def get_queryset(self):
        return Sponsorship.objects.select_related("student__user", "sponsor", "term__academic_year", "academic_year")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="Sponsorship", object_id=instance.id)

    @action(detail=False, methods=["get"])
    def report(self, request):
        """GET /api/fees/sponsorships/report/?term=<id> - per sponsor: expected, paid, outstanding."""
        term = Term.objects.filter(pk=request.query_params.get("term")).first() or Term.objects.filter(is_current=True).first()
        if term is None:
            raise ValidationError({"detail": "Choose a term."})
        return Response({"term": str(term), "sponsors": sponsorship_report(term)})


class CarryForwardViewSet(viewsets.ModelViewSet):
    permission_classes = [FinanceAccessPermission]
    serializer_class = CarryForwardSerializer
    filterset_fields = ["student", "from_term", "to_term"]
    search_fields = ["student__index_number", "student__user__first_name", "student__user__last_name"]

    def get_queryset(self):
        return CarryForward.objects.select_related("student__user", "from_term__academic_year", "to_term__academic_year")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="CarryForward", object_id=instance.id)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """POST /api/fees/carry-forward/generate/ {from_term, to_term} - carry unpaid balances forward."""
        from_term = Term.objects.filter(pk=request.data.get("from_term")).first()
        to_term = Term.objects.filter(pk=request.data.get("to_term")).first()
        if not from_term or not to_term:
            raise ValidationError({"detail": "Choose the term to carry from and the term to carry into."})
        if from_term.start_date >= to_term.start_date:
            raise ValidationError({"detail": "The term to carry into must come after the term to carry from."})
        result = generate_carry_forward(from_term, to_term, user=request.user)
        log_action(
            user=request.user, action="create", model_name="CarryForward",
            description=f"Carried forward {result['total']} for {result['students']} student(s) from {from_term} to {to_term}",
        )
        return Response(result)


class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [FinanceAccessPermission]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    filterset_fields = ["category", "method"]
    search_fields = ["description", "paid_to", "reference"]

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="Expense", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="Expense", object_id=instance.id)


class OtherIncomeViewSet(viewsets.ModelViewSet):
    permission_classes = [FinanceAccessPermission]
    serializer_class = OtherIncomeSerializer
    queryset = OtherIncome.objects.all()
    filterset_fields = ["category", "method"]
    search_fields = ["description", "received_from", "reference"]

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="OtherIncome", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="OtherIncome", object_id=instance.id)


class StaffSalaryViewSet(viewsets.ModelViewSet):
    permission_classes = [FinanceAccessPermission]
    serializer_class = StaffSalarySerializer
    filterset_fields = ["staff", "year", "month", "status"]
    search_fields = ["staff__first_name", "staff__last_name", "staff__username"]

    def get_queryset(self):
        return StaffSalary.objects.select_related("staff")

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="StaffSalary", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="StaffSalary", object_id=instance.id)

    @action(detail=False, methods=["get"])
    def staff(self, request):
        """GET /api/fees/salaries/staff/ - active staff members, for the salary form."""
        users = User.objects.filter(role__in=STAFF_ROLES, is_active=True).order_by("first_name", "last_name")
        return Response([{"id": u.id, "name": u.get_full_name() or u.username, "role": u.get_role_display()} for u in users])

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """POST /api/fees/salaries/generate/ {year, month} - create the month's pending pay lines for all staff."""
        try:
            year, month = int(request.data.get("year")), int(request.data.get("month"))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Choose a year and a month."})
        if not 1 <= month <= 12:
            raise ValidationError({"detail": "Month must be between 1 and 12."})
        result = generate_payroll(year, month, user=request.user)
        log_action(user=request.user, action="create", model_name="StaffSalary", description=f"Generated payroll {year}-{month:02d}: {result}")
        return Response(result)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """POST /api/fees/salaries/{id}/mark-paid/ {paid_date?, method?, reference?}"""
        salary = self.get_object()
        salary.status = StaffSalary.Status.PAID
        salary.paid_date = request.data.get("paid_date") or salary.paid_date
        salary.method = request.data.get("method") or salary.method
        salary.reference = request.data.get("reference") or salary.reference
        salary.save()
        log_action(user=request.user, action="update", model_name="StaffSalary", object_id=salary.id, description="Marked salary as paid")
        return Response(StaffSalarySerializer(salary).data)


class FinanceSummaryView(APIView):
    """GET /api/fees/finance/summary/?start=YYYY-MM-DD&end=YYYY-MM-DD - income and expenditure statement."""

    permission_classes = [FinanceAccessPermission]

    def get(self, request):
        try:
            today = date.today()
            start = date.fromisoformat(request.query_params.get("start") or f"{today.year}-01-01")
            end = date.fromisoformat(request.query_params.get("end") or today.isoformat())
        except ValueError:
            raise ValidationError({"detail": "Dates must look like 2026-01-31."})
        if start > end:
            raise ValidationError({"detail": "The start date is after the end date."})
        return Response(finance_summary(start, end))


class ArrearsView(APIView):
    """GET /api/fees/finance/arrears/?term=<id>&school_class=<id> - students who have not fully paid."""

    permission_classes = [FinanceAccessPermission]

    def get(self, request):
        term = Term.objects.filter(pk=request.query_params.get("term")).first() or Term.objects.filter(is_current=True).first()
        if term is None:
            raise ValidationError({"detail": "Choose a term."})
        school_class = None
        if request.query_params.get("school_class"):
            from apps.classes.models import SchoolClass

            school_class = SchoolClass.objects.filter(pk=request.query_params["school_class"]).first()
        rows = arrears_for_term(term, school_class)
        return Response({"term": str(term), "count": len(rows), "total": sum((r["balance"] for r in rows), 0), "students": rows})
