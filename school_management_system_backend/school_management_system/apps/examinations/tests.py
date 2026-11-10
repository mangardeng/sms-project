from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.classes.models import SchoolClass
from apps.core.models import AcademicYear, Term
from apps.examinations.models import (
    ExamMarkAuditLog,
    Examination,
    ExaminationResult,
    ExaminationType,
    GradeBoundary,
    SubjectTermResult,
    TermSummary,
)
from apps.students.models import Student
from apps.subjects.models import Subject

User = get_user_model()


def make_student(username, school_class):
    user = User.objects.create_user(username=username, password="x", role="student", first_name=username, last_name="Test")
    return Student.objects.create(user=user, school_class=school_class)


class TermResultTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = AcademicYear.objects.create(name="2026/2027", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
        cls.term = Term.objects.create(academic_year=cls.year, name="term_1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1), is_current=True)
        cls.klass = SchoolClass.objects.create(name="Grade 7", level=7)
        cls.math = Subject.objects.create(name="Mathematics", code="MATH")
        cls.eng = Subject.objects.create(name="English", code="ENG")
        cls.mid = ExaminationType.objects.create(name="Midterm", category="midterm", weight_percentage=40)
        cls.end = ExaminationType.objects.create(name="End of Term", category="end_term", weight_percentage=60)
        cls.admin = User.objects.create_user(username="boss", password="x", role="admin", is_superuser=True)
        cls.ann = make_student("ann", cls.klass)
        cls.bob = make_student("bob", cls.klass)

    def exam(self, subject, exam_type, max_marks=100):
        return Examination.objects.create(
            name=f"{exam_type.name} {subject.code}", examination_type=exam_type, school_class=self.klass,
            subject=subject, academic_year=self.year, term=self.term, date=date(2026, 2, 1), max_marks=max_marks,
        )

    def mark(self, exam, student, marks):
        return ExaminationResult.objects.create(examination=exam, student=student, marks_obtained=Decimal(marks))

    def test_midterm_only_is_provisional_then_combined_with_end_term(self):
        mid, end = self.exam(self.math, self.mid, max_marks=40), self.exam(self.math, self.end, max_marks=60)
        self.mark(mid, self.ann, 32)  # 32 / 40 = 80%

        row = SubjectTermResult.objects.get(student=self.ann, subject=self.math)
        self.assertEqual(row.final_percentage, Decimal("80.00"))
        self.assertEqual(row.grade, "A")
        self.assertFalse(row.is_complete)
        self.assertIsNone(row.endterm_percentage)

        self.mark(end, self.ann, 30)  # 32 + 30 = 62 out of 100
        row.refresh_from_db()
        self.assertEqual(row.midterm_percentage, Decimal("80.00"))
        self.assertEqual(row.endterm_percentage, Decimal("50.00"))
        self.assertEqual(row.final_percentage, Decimal("62.00"))
        self.assertEqual((row.midterm_points, row.endterm_points), (Decimal("32.00"), Decimal("30.00")))
        self.assertEqual(row.grade, "C")
        self.assertEqual(row.remark, "Good")
        self.assertTrue(row.is_complete)

    def test_marks_out_of_other_totals_are_converted_to_percentages(self):
        mid = self.exam(self.math, self.mid, max_marks=50)
        self.mark(mid, self.ann, 40)
        self.assertEqual(SubjectTermResult.objects.get(student=self.ann).midterm_percentage, Decimal("80.00"))

    def test_overall_average_grade_and_positions(self):
        for subject in (self.math, self.eng):
            mid, end = self.exam(subject, self.mid), self.exam(subject, self.end)
            self.mark(mid, self.ann, 90)
            self.mark(end, self.ann, 90)
            self.mark(mid, self.bob, 50)
            self.mark(end, self.bob, 50)

        ann = TermSummary.objects.get(student=self.ann)
        bob = TermSummary.objects.get(student=self.bob)
        self.assertEqual((ann.subjects_count, ann.average_percentage, ann.grade, ann.position, ann.class_size), (2, Decimal("90.00"), "A", 1, 2))
        self.assertEqual((bob.average_percentage, bob.grade, bob.position), (Decimal("50.00"), "D", 2))
        self.assertEqual(ann.total_score, Decimal("180.00"))
        self.assertTrue(ann.is_complete)
        self.assertEqual(SubjectTermResult.objects.get(student=self.bob, subject=self.math).position, 2)

    def test_correcting_a_mark_updates_everything(self):
        mid = self.exam(self.math, self.mid)
        result = self.mark(mid, self.ann, 40)
        self.mark(mid, self.bob, 60)
        self.assertEqual(TermSummary.objects.get(student=self.ann).position, 2)

        result.marks_obtained = Decimal("95")
        result.save()
        self.assertEqual(TermSummary.objects.get(student=self.ann).position, 1)
        self.assertEqual(TermSummary.objects.get(student=self.ann).grade, "A")

    def test_deleting_a_mark_removes_the_computed_result(self):
        mid = self.exam(self.math, self.mid)
        result = self.mark(mid, self.ann, 70)
        self.assertTrue(TermSummary.objects.filter(student=self.ann).exists())
        result.delete()
        self.assertFalse(SubjectTermResult.objects.filter(student=self.ann).exists())
        self.assertFalse(TermSummary.objects.filter(student=self.ann).exists())

    def test_exams_that_are_neither_midterm_nor_end_term_do_not_count(self):
        mock = ExaminationType.objects.create(name="Mock", category="other")
        self.mark(self.exam(self.math, mock), self.ann, 10)
        self.assertFalse(SubjectTermResult.objects.exists())

    def test_marks_are_simply_added_whatever_the_old_weights_say(self):
        self.mid.weight_percentage = Decimal("100")
        self.end.weight_percentage = Decimal("100")
        self.mid.save()
        self.end.save()
        self.mark(self.exam(self.math, self.mid, max_marks=40), self.ann, 36)
        self.mark(self.exam(self.math, self.end, max_marks=60), self.ann, 56)
        row = SubjectTermResult.objects.get(student=self.ann)
        self.assertEqual(row.final_percentage, Decimal("92.00"))
        self.assertEqual(row.grade, "A")
        self.assertEqual(row.remark, "Excellent")

    def test_exam_out_of_defaults_from_its_type(self):
        self.client.force_authenticate(self.admin)
        payload = {"name": "T1 Midterm Math", "examination_type": self.mid.id, "school_class": self.klass.id,
                   "subject": self.math.id, "academic_year": self.year.id, "term": self.term.id, "date": "2026-02-01"}
        response = self.client.post("/api/examinations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Decimal(response.json()["max_marks"]), Decimal("40"))
        payload.update(name="T1 End Math", examination_type=self.end.id)
        self.assertEqual(Decimal(self.client.post("/api/examinations/", payload, format="json").json()["max_marks"]), Decimal("60"))

    def test_changing_grade_scale_regrades_everything(self):
        self.mark(self.exam(self.math, self.mid), self.ann, 85)
        self.assertEqual(ExaminationResult.objects.get().grade, "A")
        self.client.force_authenticate(self.admin)
        boundary = GradeBoundary.objects.get(grade="A")
        response = self.client.patch(f"/api/examinations/grade-scale/{boundary.id}/", {"min_percentage": "90"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ExaminationResult.objects.get().grade, "B")
        self.assertEqual(SubjectTermResult.objects.get().grade, "B")

    def test_bulk_entry_grades_whole_class_and_rejects_marks_above_maximum(self):
        mid = self.exam(self.math, self.mid)
        self.client.force_authenticate(self.admin)

        bad = self.client.post("/api/examinations/results/bulk-entry/", {
            "examination": mid.id, "entries": [{"student": self.ann.id, "marks_obtained": "101"}],
        }, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(ExaminationResult.objects.exists())

        ok = self.client.post("/api/examinations/results/bulk-entry/", {
            "examination": mid.id,
            "entries": [{"student": self.ann.id, "marks_obtained": "75"}, {"student": self.bob.id, "marks_obtained": "45"}],
        }, format="json")
        self.assertEqual(ok.status_code, 200)
        grades = {r["student_index_number"]: r["grade"] for r in ok.json()}
        self.assertEqual(sorted(grades.values()), ["B", "E"])
        self.assertEqual(TermSummary.objects.count(), 2)

    def test_students_only_see_their_own_published_results(self):
        mid = self.exam(self.math, self.mid)
        self.mark(mid, self.ann, 80)
        self.mark(mid, self.bob, 60)

        self.client.force_authenticate(self.ann.user)
        self.assertEqual(self.client.get("/api/examinations/term-summaries/").json()["count"], 0)  # not published yet

        self.client.force_authenticate(self.admin)
        mid_pk = mid.pk
        self.assertEqual(self.client.post(f"/api/examinations/{mid_pk}/publish/").status_code, 200)

        self.client.force_authenticate(self.ann.user)
        data = self.client.get("/api/examinations/term-summaries/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["student"], self.ann.id)
        card = self.client.get(f"/api/examinations/term-summaries/{data['results'][0]['id']}/report-card/").json()
        self.assertEqual(len(card["subjects"]), 1)
        self.assertEqual(self.client.post("/api/examinations/term-summaries/recompute/", {}).status_code, 403)

    def test_recompute_endpoint_rebuilds_a_class(self):
        self.mark(self.exam(self.math, self.mid), self.ann, 80)
        TermSummary.objects.all().delete()
        SubjectTermResult.objects.all().delete()
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/examinations/term-summaries/recompute/", {"school_class": self.klass.id, "term": self.term.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TermSummary.objects.count(), 1)


class MidtermOutOf40EndOutOf60Tests(TermResultTests):
    """Midterm marked out of 40 and end of term out of 60 (weights 40 / 60) simply add up to 100."""

    def test_36_of_40_plus_56_of_60_is_92_and_ranking_follows_totals(self):
        math_mid, math_end = self.exam(self.math, self.mid, max_marks=40), self.exam(self.math, self.end, max_marks=60)
        eng_mid, eng_end = self.exam(self.eng, self.mid, max_marks=40), self.exam(self.eng, self.end, max_marks=60)
        for exam, ann, bob in ((math_mid, 36, 30), (math_end, 56, 45), (eng_mid, 30, 35), (eng_end, 50, 50)):
            self.mark(exam, self.ann, ann)
            self.mark(exam, self.bob, bob)

        math = SubjectTermResult.objects.get(student=self.ann, subject=self.math)
        self.assertEqual((math.midterm_points, math.midterm_out_of), (Decimal("36.00"), Decimal("40.00")))
        self.assertEqual((math.endterm_points, math.endterm_out_of), (Decimal("56.00"), Decimal("60.00")))
        self.assertEqual(math.final_percentage, Decimal("92.00"))
        self.assertEqual(math.grade, "A")

        # Ann: math 92, english 30+50=80 -> average 86 (A), Bob: math 75, english 85 -> average 80 (A) -> Ann 1st
        ann, bob = TermSummary.objects.get(student=self.ann), TermSummary.objects.get(student=self.bob)
        self.assertEqual((ann.total_score, ann.average_percentage, ann.grade, ann.position), (Decimal("172.00"), Decimal("86.00"), "A", 1))
        self.assertEqual((bob.average_percentage, bob.position), (Decimal("80.00"), 2))
        self.assertTrue(ann.is_complete)


class ExamTypeCategoryGuessTests(TermResultTests):
    def test_types_created_without_a_category_are_still_counted(self):
        mid = ExaminationType.objects.create(name="Mid Term Exam", weight_percentage=40)
        end = ExaminationType.objects.create(name="End of Term Exam", weight_percentage=60)
        mock = ExaminationType.objects.create(name="Weekly Quiz")
        self.assertEqual((mid.category, end.category, mock.category), ("midterm", "end_term", "other"))

        for exam_type, max_marks, marks in ((mid, 40, 36), (end, 60, 56)):
            self.mark(self.exam(self.math, exam_type, max_marks=max_marks), self.ann, marks)
        self.assertEqual(SubjectTermResult.objects.get(student=self.ann).final_percentage, Decimal("92.00"))


class GenerateSampleResultsTests(TermResultTests):
    def test_command_creates_marks_and_calculates_everything(self):
        from django.core.management import call_command

        call_command("generate_sample_results", "--seed", "1", "--publish", verbosity=0)
        # 2 subjects x (midterm + end of term) for each of the 2 students
        self.assertEqual(ExaminationResult.objects.count(), 8)
        row = SubjectTermResult.objects.filter(student=self.ann).first()
        self.assertTrue(row.is_complete and row.is_published)
        self.assertEqual(row.midterm_out_of + row.endterm_out_of, Decimal("100.00"))
        self.assertEqual(sorted(TermSummary.objects.values_list("position", flat=True)), [1, 2])


class LegacyMarksTests(TermResultTests):
    def test_marks_entered_before_the_feature_are_calculated_when_results_are_opened(self):
        from apps.examinations.services import suspend_auto_compute

        with suspend_auto_compute():  # simulates marks that were saved before term results existed
            exam = self.exam(self.math, self.mid, max_marks=100)
            exam.is_published = True
            exam.save()
            self.mark(exam, self.ann, 45)
        self.assertFalse(TermSummary.objects.exists())

        self.client.force_authenticate(self.ann.user)
        data = self.client.get("/api/examinations/term-summaries/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["average_percentage"], "45.00")
        self.assertEqual(data["results"][0]["grade"], "E")


class SubjectSheetTests(APITestCase):
    """Subject teacher / administrator enters midterm + end-of-term marks; everything else is automatic."""

    @classmethod
    def setUpTestData(cls):
        from apps.subjects.models import ClassSubject
        from apps.teachers.models import Teacher

        cls.year = AcademicYear.objects.create(name="2026/2027", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
        cls.term = Term.objects.create(academic_year=cls.year, name="term_1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1), is_current=True)
        cls.klass = SchoolClass.objects.create(name="Grade 7", level=7)
        cls.math = Subject.objects.create(name="Mathematics", code="MATH")
        cls.eng = Subject.objects.create(name="English", code="ENG")
        cls.admin = User.objects.create_user(username="boss", password="x", role="admin", is_superuser=True)
        cls.math_teacher = Teacher.objects.create(user=User.objects.create_user(username="tm", password="x", role="teacher"), staff_id="T1")
        cls.eng_teacher = Teacher.objects.create(user=User.objects.create_user(username="te", password="x", role="teacher"), staff_id="T2")
        ClassSubject.objects.create(school_class=cls.klass, subject=cls.math, teacher=cls.math_teacher, academic_year=cls.year)
        ClassSubject.objects.create(school_class=cls.klass, subject=cls.eng, teacher=cls.eng_teacher, academic_year=cls.year)
        cls.ann = make_student("ann", cls.klass)
        cls.bob = make_student("bob", cls.klass)

    def payload(self, **extra):
        data = {"school_class": self.klass.id, "subject": self.math.id, "term": self.term.id,
                "entries": [{"student": self.ann.id, "midterm_marks": "36", "endterm_marks": "56"},
                            {"student": self.bob.id, "midterm_marks": "20"}]}
        data.update(extra)
        return data

    def test_subject_teacher_enters_marks_and_everything_is_calculated(self):
        self.client.force_authenticate(self.math_teacher.user)
        response = self.client.post("/api/examinations/subject-sheet/", self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.content)
        rows = {r["student_index_number"]: r for r in response.json()["rows"]}
        ann = rows[self.ann.index_number]
        self.assertEqual((Decimal(ann["total"]), Decimal(ann["percentage"]), ann["grade"], ann["remark"]), (Decimal("92"), Decimal("92"), "A", "Excellent"))
        bob = rows[self.bob.index_number]  # only the midterm so far: 20/40 = 50% (provisional)
        self.assertEqual((Decimal(bob["percentage"]), bob["grade"], bob["is_complete"]), (Decimal("50"), "D", False))
        self.assertEqual((ann["position"], bob["position"]), (1, 2))
        self.assertEqual(Decimal(response.json()["midterm"]["out_of"]), Decimal("40"))
        self.assertEqual(Decimal(response.json()["endterm"]["out_of"]), Decimal("60"))
        self.assertEqual(TermSummary.objects.get(student=self.ann).grade, "A")

    def test_another_subjects_teacher_is_refused(self):
        self.client.force_authenticate(self.eng_teacher.user)
        self.assertEqual(self.client.post("/api/examinations/subject-sheet/", self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/examinations/subject-sheet/", {"school_class": self.klass.id, "subject": self.math.id, "term": self.term.id}).status_code, 403)

    def test_options_list_only_the_teachers_own_subjects(self):
        self.client.force_authenticate(self.math_teacher.user)
        options = self.client.get("/api/examinations/subject-sheet/options/").json()
        self.assertEqual([o["subject_name"] for o in options], ["Mathematics"])
        self.client.force_authenticate(self.admin)
        self.assertEqual(len(self.client.get("/api/examinations/subject-sheet/options/").json()), 2)

    def test_published_marks_can_be_corrected_with_a_reason_and_are_audited(self):
        self.client.force_authenticate(self.math_teacher.user)
        self.client.post("/api/examinations/subject-sheet/", self.payload(), format="json")
        self.client.force_authenticate(self.admin)
        for exam in Examination.objects.all():
            self.client.post(f"/api/examinations/{exam.id}/publish/")

        fix = self.payload(entries=[{"student": self.ann.id, "midterm_marks": "38"}])
        self.client.force_authenticate(self.math_teacher.user)
        refused = self.client.post("/api/examinations/subject-sheet/", fix, format="json")
        self.assertEqual(refused.status_code, 400)  # reason required once published

        fix["reason"] = "Typing mistake in the midterm"
        ok = self.client.post("/api/examinations/subject-sheet/", fix, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(SubjectTermResult.objects.get(student=self.ann).final_percentage, Decimal("94.00"))
        log = ExamMarkAuditLog.objects.get()
        self.assertEqual((log.old_marks, log.new_marks, log.reason), (Decimal("36"), Decimal("38"), "Typing mistake in the midterm"))

    def test_teacher_remark_replaces_the_automatic_remark_and_survives_recalculation(self):
        self.client.force_authenticate(self.math_teacher.user)
        self.client.post("/api/examinations/subject-sheet/", self.payload(entries=[
            {"student": self.ann.id, "midterm_marks": "36", "endterm_marks": "56", "remark": "Outstanding work"}]), format="json")
        row = SubjectTermResult.objects.get(student=self.ann)
        self.assertEqual((row.remark, row.teacher_remark), ("Excellent", "Outstanding work"))
        self.client.force_authenticate(self.admin)
        card = self.client.get(f"/api/examinations/term-summaries/{TermSummary.objects.get(student=self.ann).id}/report-card/").json()
        self.assertEqual(card["subjects"][0]["remark"], "Outstanding work")
        self.assertEqual(card["subjects"][0]["auto_remark"], "Excellent")
        from apps.examinations.services import recompute_all
        recompute_all()
        self.assertEqual(SubjectTermResult.objects.get(student=self.ann).teacher_remark, "Outstanding work")

    def test_marks_above_the_maximum_are_rejected(self):
        self.client.force_authenticate(self.math_teacher.user)
        bad = self.payload(entries=[{"student": self.ann.id, "midterm_marks": "41"}])
        self.assertEqual(self.client.post("/api/examinations/subject-sheet/", bad, format="json").status_code, 400)
        self.assertFalse(ExaminationResult.objects.exists())

    def test_subject_teacher_can_correct_a_published_mark_through_the_normal_marks_api(self):
        self.client.force_authenticate(self.math_teacher.user)
        self.client.post("/api/examinations/subject-sheet/", self.payload(), format="json")
        exam = Examination.objects.get(examination_type__category="midterm")
        exam.is_published = True
        exam.marks_locked = True
        exam.save()
        result = ExaminationResult.objects.get(examination=exam, student=self.ann)
        url = f"/api/examinations/results/{result.id}/"
        self.assertEqual(self.client.patch(url, {"marks_obtained": "30"}, format="json").status_code, 400)  # needs a reason
        done = self.client.patch(url, {"marks_obtained": "30", "reason": "Wrong script"}, format="json")
        self.assertEqual(done.status_code, 200, done.content)
        # a teacher of a different subject cannot
        self.client.force_authenticate(self.eng_teacher.user)
        self.assertEqual(self.client.patch(url, {"marks_obtained": "10", "reason": "x"}, format="json").status_code, 403)
