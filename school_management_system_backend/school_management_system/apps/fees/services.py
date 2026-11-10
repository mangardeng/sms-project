"""Fee statements, carry-forward, sponsorship, payroll and the income & expenditure summary."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import User
from apps.fees.models import (
    CarryForward,
    Expense,
    FeeStructure,
    OtherIncome,
    Payment,
    Sponsor,
    Sponsorship,
    StaffSalary,
)
from apps.students.models import Student

ZERO = Decimal("0")
STAFF_ROLES = (
    User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.ACCOUNTANT,
    User.Role.LIBRARIAN, User.Role.REGISTRAR,
)


def _sum(values):
    return sum(values, ZERO)


# ---------------------------------------------------------------------------
# One student, one term
# ---------------------------------------------------------------------------
def term_statement(student, term):
    """Everything the family and the accountant need to know about a student's account for a term."""
    due = _sum(FeeStructure.objects.filter(school_class=student.school_class, term=term).values_list("amount", flat=True))
    payments = Payment.objects.filter(student=student, fee_structure__term=term, is_void=False)
    paid = _sum(payments.values_list("amount_paid", flat=True))
    sponsor_paid = _sum(payments.filter(sponsor__isnull=False).values_list("amount_paid", flat=True))
    carried = _sum(CarryForward.objects.filter(student=student, to_term=term).values_list("amount", flat=True))

    sponsorships = [s for s in Sponsorship.objects.filter(student=student).select_related("sponsor") if s.covers_term(term)]
    sponsor_share = min(due, _sum(s.share_of(due) for s in sponsorships))
    family_share = due - sponsor_share

    return {
        "fees_due": due,
        "paid": paid,
        "carried_forward": carried,
        "balance": due + carried - paid,
        "sponsor_names": ", ".join(s.sponsor.name for s in sponsorships),
        "sponsor_share": sponsor_share,
        "sponsor_paid": sponsor_paid,
        "sponsor_outstanding": max(ZERO, sponsor_share - sponsor_paid),
        "family_share": family_share,
        "family_paid": paid - sponsor_paid,
        "family_outstanding": max(ZERO, family_share + carried - (paid - sponsor_paid)),
    }


# ---------------------------------------------------------------------------
# Carry forward unpaid balances into the next term
# ---------------------------------------------------------------------------
@transaction.atomic
def generate_carry_forward(from_term, to_term, user=None):
    """
    For every active student, carry the unpaid balance of `from_term` into `to_term`.
    Safe to run again: rows are updated, and cleared when a student has since paid up.
    The balance of `from_term` already includes anything carried into it, so arrears keep
    rolling forward term after term.
    """
    created = updated = cleared = 0
    total = ZERO
    for student in Student.objects.filter(status="active").exclude(school_class__isnull=True):
        balance = term_statement(student, from_term)["balance"]
        existing = CarryForward.objects.filter(student=student, from_term=from_term, to_term=to_term).first()
        if balance > 0:
            if existing:
                existing.amount = balance
                existing.save(update_fields=["amount", "updated_at"])
                updated += 1
            else:
                CarryForward.objects.create(
                    student=student, from_term=from_term, to_term=to_term, amount=balance, created_by=user,
                )
                created += 1
            total += balance
        elif existing:
            existing.delete()
            cleared += 1
    return {"created": created, "updated": updated, "cleared": cleared, "students": created + updated, "total": total}


# ---------------------------------------------------------------------------
# Who owes what
# ---------------------------------------------------------------------------
def arrears_for_term(term, school_class=None):
    students = Student.objects.filter(status="active").exclude(school_class__isnull=True).select_related("user", "school_class")
    if school_class:
        students = students.filter(school_class=school_class)
    rows = []
    for student in students.order_by("school_class__level", "index_number"):
        stmt = term_statement(student, term)
        if stmt["balance"] > 0:
            rows.append({
                "student": student.id,
                "student_name": student.user.get_full_name(),
                "student_index_number": student.index_number,
                "school_class_name": student.school_class.name,
                **stmt,
            })
    return rows


def sponsorship_report(term):
    """Per sponsor: students supported, what they should pay for the term, what they paid, what is left."""
    report = []
    for sponsor in Sponsor.objects.filter(is_active=True):
        students, expected, paid = [], ZERO, ZERO
        for sponsorship in sponsor.sponsorships.select_related("student__user", "student__school_class"):
            if not sponsorship.covers_term(term):
                continue
            stmt = term_statement(sponsorship.student, term)
            share = sponsorship.share_of(stmt["fees_due"])
            sponsor_paid = _sum(
                Payment.objects.filter(
                    student=sponsorship.student, sponsor=sponsor, fee_structure__term=term, is_void=False
                ).values_list("amount_paid", flat=True)
            )
            expected += share
            paid += sponsor_paid
            students.append({
                "student": sponsorship.student_id,
                "student_name": sponsorship.student.user.get_full_name(),
                "student_index_number": sponsorship.student.index_number,
                "school_class_name": sponsorship.student.school_class.name if sponsorship.student.school_class else "",
                "coverage": sponsorship.get_coverage_type_display(),
                "expected": share,
                "paid": sponsor_paid,
                "outstanding": max(ZERO, share - sponsor_paid),
            })
        if students:
            report.append({
                "sponsor": sponsor.id, "sponsor_name": sponsor.name, "students": students,
                "expected": expected, "paid": paid, "outstanding": max(ZERO, expected - paid),
            })
    return report


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------
@transaction.atomic
def generate_payroll(year, month, user=None):
    """
    Creates a pending salary line for every active staff member for the month, copying the amounts
    from their most recent salary (zero for new staff - the accountant then fills them in).
    """
    created = skipped = 0
    for staff in User.objects.filter(role__in=STAFF_ROLES, is_active=True):
        if StaffSalary.objects.filter(staff=staff, year=year, month=month).exists():
            skipped += 1
            continue
        last = StaffSalary.objects.filter(staff=staff).order_by("-year", "-month").first()
        StaffSalary.objects.create(
            staff=staff, year=year, month=month,
            basic_salary=last.basic_salary if last else ZERO,
            allowances=last.allowances if last else ZERO,
            deductions=last.deductions if last else ZERO,
            method=last.method if last else Payment.Method.BANK_TRANSFER,
            recorded_by=user,
        )
        created += 1
    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# Income and expenditure statement
# ---------------------------------------------------------------------------
def finance_summary(start, end):
    """Income (fees + other) against expenditure (expenses + salaries) between two dates."""
    fee_payments = Payment.objects.filter(is_void=False, payment_date__gte=start, payment_date__lte=end)
    other_income = OtherIncome.objects.filter(date__gte=start, date__lte=end)
    expenses = Expense.objects.filter(date__gte=start, date__lte=end)
    salaries = StaffSalary.objects.filter(status=StaffSalary.Status.PAID, paid_date__gte=start, paid_date__lte=end)

    fees_total = fee_payments.aggregate(t=Sum("amount_paid"))["t"] or ZERO
    sponsor_total = fee_payments.filter(sponsor__isnull=False).aggregate(t=Sum("amount_paid"))["t"] or ZERO
    other_total = other_income.aggregate(t=Sum("amount"))["t"] or ZERO
    expense_total = expenses.aggregate(t=Sum("amount"))["t"] or ZERO
    salary_total = salaries.aggregate(t=Sum("net_salary"))["t"] or ZERO

    def grouped(qs, key, value, labels=None):
        out = defaultdict(lambda: ZERO)
        for k, v in qs.values_list(key, value):
            out[k] += v
        return [{"key": k, "label": (labels or {}).get(k, k), "amount": v} for k, v in sorted(out.items(), key=lambda kv: -kv[1])]

    monthly = defaultdict(lambda: {"income": ZERO, "expenses": ZERO})
    for d, a in fee_payments.values_list("payment_date", "amount_paid"):
        monthly[d.strftime("%Y-%m")]["income"] += a
    for d, a in other_income.values_list("date", "amount"):
        monthly[d.strftime("%Y-%m")]["income"] += a
    for d, a in expenses.values_list("date", "amount"):
        monthly[d.strftime("%Y-%m")]["expenses"] += a
    for d, a in salaries.values_list("paid_date", "net_salary"):
        monthly[d.strftime("%Y-%m")]["expenses"] += a

    total_income = fees_total + other_total
    total_expenses = expense_total + salary_total
    return {
        "start": start, "end": end,
        "income": {
            "fees": fees_total, "fees_from_sponsors": sponsor_total, "other": other_total, "total": total_income,
            "fees_by_method": grouped(fee_payments, "method", "amount_paid", dict(Payment.Method.choices)),
            "other_by_category": grouped(other_income, "category", "amount", dict(OtherIncome.Category.choices)),
        },
        "expenditure": {
            "expenses": expense_total, "salaries": salary_total, "total": total_expenses,
            "expenses_by_category": grouped(expenses, "category", "amount", dict(Expense.Category.choices)),
        },
        "net": total_income - total_expenses,
        "monthly": [{"month": m, **v, "net": v["income"] - v["expenses"]} for m, v in sorted(monthly.items())],
    }
