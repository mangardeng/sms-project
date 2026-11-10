from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.classes.models import SchoolClass
from apps.core.models import AcademicYear, Term
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
from apps.students.models import Student

User = get_user_model()


class FeesTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = AcademicYear.objects.create(name="2026/2027", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
        cls.t1 = Term.objects.create(academic_year=cls.year, name="term_1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1), is_current=True)
        cls.t2 = Term.objects.create(academic_year=cls.year, name="term_2", start_date=date(2026, 5, 1), end_date=date(2026, 8, 1))
        cls.klass = SchoolClass.objects.create(name="Grade 7", level=7)
        cls.tuition1 = FeeStructure.objects.create(school_class=cls.klass, term=cls.t1, name="Tuition", amount=Decimal("1000"))
        cls.tuition2 = FeeStructure.objects.create(school_class=cls.klass, term=cls.t2, name="Tuition", amount=Decimal("1000"))
        cls.accountant = User.objects.create_user(username="acc", password="x", role="accountant")
        cls.admin = User.objects.create_user(username="boss", password="x", role="admin")
        cls.teacher = User.objects.create_user(username="tch", password="x", role="teacher")
        cls.ann = cls._student("ann")
        cls.bob = cls._student("bob")

    @classmethod
    def _student(cls, username):
        user = User.objects.create_user(username=username, password="x", role="student", first_name=username, last_name="T")
        return Student.objects.create(user=user, school_class=cls.klass)

    def pay(self, student, amount, structure=None, **extra):
        return Payment.objects.create(student=student, fee_structure=structure or self.tuition1, amount_paid=Decimal(amount), **extra)


class CarryForwardTests(FeesTestBase):
    def test_unpaid_balance_is_carried_into_the_next_term(self):
        self.pay(self.ann, "1000")  # paid in full
        self.pay(self.bob, "400")   # owes 600
        self.client.force_authenticate(self.accountant)
        result = self.client.post("/api/fees/carry-forward/generate/", {"from_term": self.t1.id, "to_term": self.t2.id}, format="json")
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(Decimal(str(result.json()["total"])), Decimal("600"))
        self.assertEqual(CarryForward.objects.count(), 1)
        row = CarryForward.objects.get()
        self.assertEqual((row.student, row.amount), (self.bob, Decimal("600.00")))
        self.assertEqual(student_balance(self.bob, self.t2), Decimal("1600"))  # term 2 fee + carried 600
        self.assertEqual(student_balance(self.ann, self.t2), Decimal("1000"))

    def test_arrears_keep_rolling_and_paying_later_clears_them(self):
        self.pay(self.bob, "400")
        self.client.force_authenticate(self.accountant)
        self.client.post("/api/fees/carry-forward/generate/", {"from_term": self.t1.id, "to_term": self.t2.id}, format="json")
        self.pay(self.bob, "1600", structure=self.tuition2)  # clears term 2 including the carried 600
        self.assertEqual(student_balance(self.bob, self.t2), Decimal("0"))
        self.client.post("/api/fees/carry-forward/generate/", {"from_term": self.t1.id, "to_term": self.t2.id}, format="json")
        self.assertEqual(CarryForward.objects.filter(student=self.bob).count(), 1)  # re-running never duplicates

    def test_cannot_carry_backwards(self):
        self.client.force_authenticate(self.accountant)
        response = self.client.post("/api/fees/carry-forward/generate/", {"from_term": self.t2.id, "to_term": self.t1.id}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_teachers_and_students_have_no_access(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get("/api/fees/carry-forward/").status_code, 403)
        self.client.force_authenticate(self.ann.user)
        self.assertEqual(self.client.get("/api/fees/carry-forward/").status_code, 403)


class PaymentCorrectionTests(FeesTestBase):
    def test_only_the_accountant_can_correct_and_a_reason_is_required(self):
        payment = self.pay(self.ann, "300", recorded_by=self.accountant)
        url = f"/api/fees/payments/{payment.id}/"

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(url, {"amount_paid": "350", "reason": "typo"}, format="json").status_code, 403)

        self.client.force_authenticate(self.accountant)
        self.assertEqual(self.client.patch(url, {"amount_paid": "350"}, format="json").status_code, 400)  # no reason
        ok = self.client.patch(url, {"amount_paid": "350", "method": "mobile_money", "reason": "Keyed 300 instead of 350"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        payment.refresh_from_db()
        self.assertEqual((payment.amount_paid, payment.method), (Decimal("350.00"), "mobile_money"))
        log = PaymentAuditLog.objects.get()
        self.assertIn("300.00 -> 350.00", log.changes)
        self.assertEqual(log.reason, "Keyed 300 instead of 350")
        self.assertEqual(student_balance(self.ann, self.t1), Decimal("650"))
        history = self.client.get(f"{url}history/").json()
        self.assertEqual(len(history), 1)

    def test_payments_cannot_be_deleted_but_can_be_voided(self):
        payment = self.pay(self.ann, "300")
        self.client.force_authenticate(self.accountant)
        self.assertEqual(self.client.delete(f"/api/fees/payments/{payment.id}/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/fees/payments/{payment.id}/void/", {}, format="json").status_code, 400)
        ok = self.client.post(f"/api/fees/payments/{payment.id}/void/", {"reason": "Recorded for the wrong student"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(student_balance(self.ann, self.t1), Decimal("1000"))  # no longer counted
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"/api/fees/payments/{payment.id}/void/", {"reason": "x"}, format="json").status_code, 403)

    def test_a_voided_payment_is_hidden_from_the_family(self):
        payment = self.pay(self.ann, "300")
        Payment.objects.filter(pk=payment.pk).update(is_void=True)
        self.client.force_authenticate(self.ann.user)
        self.assertEqual(self.client.get("/api/fees/payments/").json()["count"], 0)

    def test_payment_date_can_be_set_and_corrected(self):
        self.client.force_authenticate(self.accountant)
        created = self.client.post("/api/fees/payments/", {
            "student": self.ann.id, "fee_structure": self.tuition1.id, "amount_paid": "200",
            "method": "cash", "payment_date": "2026-02-10"}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()["payment_date"], "2026-02-10")
        fixed = self.client.patch(f"/api/fees/payments/{created.json()['id']}/", {"payment_date": "2026-02-12", "reason": "Wrong date"}, format="json")
        self.assertEqual(fixed.json()["payment_date"], "2026-02-12")


class SponsorshipTests(FeesTestBase):
    def test_sponsorship_splits_the_fees_between_sponsor_and_family(self):
        sponsor = Sponsor.objects.create(name="Hope Foundation")
        Sponsorship.objects.create(student=self.ann, sponsor=sponsor, coverage_type="percentage", value=Decimal("60"))
        self.pay(self.ann, "600", sponsor=sponsor)
        self.pay(self.ann, "100")
        stmt = term_statement(self.ann, self.t1)
        self.assertEqual((stmt["sponsor_share"], stmt["sponsor_paid"], stmt["sponsor_outstanding"]), (Decimal("600"), Decimal("600"), Decimal("0")))
        self.assertEqual((stmt["family_share"], stmt["family_paid"], stmt["family_outstanding"]), (Decimal("400"), Decimal("100"), Decimal("300")))
        self.assertEqual(stmt["balance"], Decimal("300"))

    def test_full_and_fixed_coverage_and_scope(self):
        sponsor = Sponsor.objects.create(name="County Bursary")
        Sponsorship.objects.create(student=self.ann, sponsor=sponsor, coverage_type="full")
        Sponsorship.objects.create(student=self.bob, sponsor=sponsor, coverage_type="fixed", value=Decimal("250"), term=self.t1)
        self.assertEqual(term_statement(self.ann, self.t1)["sponsor_share"], Decimal("1000"))
        self.assertEqual(term_statement(self.bob, self.t1)["sponsor_share"], Decimal("250"))
        self.assertEqual(term_statement(self.bob, self.t2)["sponsor_share"], Decimal("0"))  # only term 1

    def test_report_and_validation(self):
        self.client.force_authenticate(self.accountant)
        sponsor = self.client.post("/api/fees/sponsors/", {"name": "Hope Foundation", "sponsor_type": "organization"}, format="json").json()
        bad = self.client.post("/api/fees/sponsorships/", {"student": self.ann.id, "sponsor": sponsor["id"], "coverage_type": "percentage", "value": "150"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post("/api/fees/sponsorships/", {"student": self.ann.id, "sponsor": sponsor["id"], "coverage_type": "full"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.pay(self.ann, "400", sponsor=Sponsor.objects.get())
        report = self.client.get(f"/api/fees/sponsorships/report/?term={self.t1.id}").json()
        row = report["sponsors"][0]
        self.assertEqual((Decimal(str(row["expected"])), Decimal(str(row["paid"])), Decimal(str(row["outstanding"]))), (Decimal("1000"), Decimal("400"), Decimal("600")))

    def test_balance_endpoint_exposes_the_breakdown(self):
        Sponsorship.objects.create(student=self.ann, sponsor=Sponsor.objects.create(name="Hope"), coverage_type="full")
        self.client.force_authenticate(self.ann.user)
        data = self.client.get("/api/fees/balance/").json()
        self.assertEqual(data["statement"]["sponsor_names"], "Hope")
        self.assertEqual(Decimal(str(data["statement"]["sponsor_share"])), Decimal("1000"))


class IncomeExpenseSalaryTests(FeesTestBase):
    def test_income_and_expenditure_statement(self):
        self.pay(self.ann, "500", payment_date=date(2026, 2, 5))
        self.pay(self.bob, "300", payment_date=date(2026, 3, 5))
        voided = self.pay(self.bob, "999", payment_date=date(2026, 3, 6))
        Payment.objects.filter(pk=voided.pk).update(is_void=True)
        OtherIncome.objects.create(date=date(2026, 2, 20), category="donation", description="Donation", amount=Decimal("200"))
        Expense.objects.create(date=date(2026, 2, 25), category="utilities", description="Power", amount=Decimal("150"))
        StaffSalary.objects.create(staff=self.teacher, year=2026, month=2, basic_salary=Decimal("400"), allowances=Decimal("50"),
                                   deductions=Decimal("20"), status="paid", paid_date=date(2026, 2, 28))
        StaffSalary.objects.create(staff=self.accountant, year=2026, month=2, basic_salary=Decimal("999"))  # pending: not counted yet

        self.client.force_authenticate(self.accountant)
        data = self.client.get("/api/fees/finance/summary/?start=2026-01-01&end=2026-03-31").json()
        self.assertEqual(Decimal(str(data["income"]["fees"])), Decimal("800"))
        self.assertEqual(Decimal(str(data["income"]["total"])), Decimal("1000"))
        self.assertEqual(Decimal(str(data["expenditure"]["salaries"])), Decimal("430"))
        self.assertEqual(Decimal(str(data["expenditure"]["total"])), Decimal("580"))
        self.assertEqual(Decimal(str(data["net"])), Decimal("420"))
        self.assertEqual([m["month"] for m in data["monthly"]], ["2026-02", "2026-03"])

    def test_payroll_generation_copies_last_month_and_is_repeatable(self):
        StaffSalary.objects.create(staff=self.teacher, year=2026, month=1, basic_salary=Decimal("400"), allowances=Decimal("50"), status="paid")
        self.client.force_authenticate(self.accountant)
        first = self.client.post("/api/fees/salaries/generate/", {"year": 2026, "month": 2}, format="json")
        self.assertEqual(first.status_code, 200, first.content)
        feb = StaffSalary.objects.get(staff=self.teacher, year=2026, month=2)
        self.assertEqual((feb.basic_salary, feb.net_salary, feb.status), (Decimal("400.00"), Decimal("450.00"), "pending"))
        again = self.client.post("/api/fees/salaries/generate/", {"year": 2026, "month": 2}, format="json").json()
        self.assertEqual(again["created"], 0)

        paid = self.client.post(f"/api/fees/salaries/{feb.id}/mark-paid/", {"paid_date": "2026-02-28"}, format="json")
        self.assertEqual(paid.status_code, 200)
        feb.refresh_from_db()
        self.assertEqual((feb.status, str(feb.paid_date)), ("paid", "2026-02-28"))

    def test_net_salary_is_calculated(self):
        self.client.force_authenticate(self.accountant)
        response = self.client.post("/api/fees/salaries/", {
            "staff": self.teacher.id, "year": 2026, "month": 3, "basic_salary": "500", "allowances": "100", "deductions": "40", "method": "cash"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Decimal(response.json()["net_salary"]), Decimal("560"))

    def test_expense_and_income_are_accountant_or_admin_only(self):
        self.client.force_authenticate(self.accountant)
        self.assertEqual(self.client.post("/api/fees/expenses/", {"date": "2026-02-01", "category": "supplies", "description": "Chalk", "amount": "20", "method": "cash"}, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/fees/other-income/", {"date": "2026-02-01", "category": "grant", "description": "Grant", "amount": "500", "method": "bank_transfer"}, format="json").status_code, 201)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get("/api/fees/expenses/").status_code, 403)
        self.assertEqual(self.client.get("/api/fees/finance/summary/").status_code, 403)

    def test_arrears_list(self):
        self.pay(self.ann, "1000")
        self.pay(self.bob, "250")
        self.client.force_authenticate(self.accountant)
        data = self.client.get(f"/api/fees/finance/arrears/?term={self.t1.id}").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["students"][0]["student_name"], "bob T")
        self.assertEqual(Decimal(str(data["students"][0]["balance"])), Decimal("750"))
