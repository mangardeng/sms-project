from decimal import Decimal

from rest_framework import serializers

from apps.core.models import Term
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
    student_balance,
)
from apps.fees.services import term_statement


class FeeStructureSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.CharField(source="term.__str__", read_only=True)

    class Meta:
        model = FeeStructure
        fields = ("id", "school_class", "school_class_name", "term", "term_name", "name", "amount", "is_mandatory", "created_by")
        read_only_fields = ("created_by",)


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    fee_structure_name = serializers.CharField(source="fee_structure.name", read_only=True)
    sponsor_name = serializers.CharField(source="sponsor.name", read_only=True, default="")
    reason = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Payment
        fields = (
            "id", "student", "student_name", "student_index_number", "fee_structure",
            "fee_structure_name", "amount_paid", "method", "receipt_number",
            "payment_date", "recorded_by", "notes", "sponsor", "sponsor_name",
            "is_void", "void_reason", "reason",
        )
        read_only_fields = ("receipt_number", "recorded_by", "is_void", "void_reason")

    def validate_amount_paid(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

    def validate(self, attrs):
        student = attrs.get("student") or getattr(self.instance, "student", None)
        structure = attrs.get("fee_structure") or getattr(self.instance, "fee_structure", None)
        changed = "student" in attrs or "fee_structure" in attrs
        if changed and student and structure and student.school_class_id and structure.school_class_id != student.school_class_id:
            raise serializers.ValidationError({"fee_structure": "This fee belongs to a different class than the student's class."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("reason", None)
        return super().create(validated_data)


class PaymentAuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True, default="")

    class Meta:
        model = PaymentAuditLog
        fields = ("id", "action", "changes", "reason", "changed_by_name", "changed_at")


class StudentFeeBalanceSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_index_number = serializers.CharField()
    student_name = serializers.CharField()
    term = serializers.CharField(allow_null=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)

    @staticmethod
    def build(student, term=None):
        data = {
            "student_id": student.id,
            "student_index_number": student.index_number,
            "student_name": student.user.get_full_name(),
            "term": str(term) if term else None,
            "balance": student_balance(student, term=term),
        }
        # Breakdown for the chosen term, or the current term when none was chosen.
        statement_term = term or Term.objects.filter(is_current=True).first()
        if statement_term and student.school_class_id:
            data["statement_term"] = str(statement_term)
            data["statement"] = term_statement(student, statement_term)
        return data


class SponsorSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Sponsor
        fields = ("id", "name", "sponsor_type", "contact_person", "phone", "email", "notes", "is_active", "students_count")

    def get_students_count(self, obj):
        return obj.sponsorships.filter(is_active=True).count()


class SponsorshipSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    sponsor_name = serializers.CharField(source="sponsor.name", read_only=True)
    term_name = serializers.CharField(source="term.__str__", read_only=True, default="All terms")
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True, default="All years")

    class Meta:
        model = Sponsorship
        fields = (
            "id", "student", "student_name", "student_index_number", "sponsor", "sponsor_name",
            "coverage_type", "value", "academic_year", "academic_year_name", "term", "term_name",
            "notes", "is_active",
        )

    def validate(self, attrs):
        coverage = attrs.get("coverage_type", getattr(self.instance, "coverage_type", Sponsorship.Coverage.FULL))
        value = attrs.get("value", getattr(self.instance, "value", Decimal("0")))
        if coverage == Sponsorship.Coverage.PERCENTAGE and not (Decimal("0") < value <= Decimal("100")):
            raise serializers.ValidationError({"value": "Enter a percentage between 1 and 100."})
        if coverage == Sponsorship.Coverage.FIXED and value <= 0:
            raise serializers.ValidationError({"value": "Enter the amount the sponsor pays per term."})
        return attrs


class CarryForwardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    from_term_name = serializers.CharField(source="from_term.__str__", read_only=True)
    to_term_name = serializers.CharField(source="to_term.__str__", read_only=True)

    class Meta:
        model = CarryForward
        fields = (
            "id", "student", "student_name", "student_index_number", "from_term", "from_term_name",
            "to_term", "to_term_name", "amount", "notes",
        )


class ExpenseSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Expense
        fields = ("id", "date", "category", "category_label", "description", "amount", "paid_to", "method", "reference", "recorded_by")
        read_only_fields = ("recorded_by",)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class OtherIncomeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = OtherIncome
        fields = ("id", "date", "category", "category_label", "description", "amount", "received_from", "method", "reference", "recorded_by")
        read_only_fields = ("recorded_by",)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class StaffSalarySerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.get_full_name", read_only=True)
    staff_role = serializers.CharField(source="staff.get_role_display", read_only=True)
    period = serializers.SerializerMethodField()

    class Meta:
        model = StaffSalary
        fields = (
            "id", "staff", "staff_name", "staff_role", "year", "month", "period", "basic_salary", "allowances",
            "deductions", "net_salary", "status", "paid_date", "method", "reference", "notes",
        )
        read_only_fields = ("net_salary",)

    def get_period(self, obj):
        return f"{obj.year}-{obj.month:02d}"

    def validate_month(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Month must be between 1 and 12.")
        return value
