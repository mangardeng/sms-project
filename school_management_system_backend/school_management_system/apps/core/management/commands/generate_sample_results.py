import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.classes.models import SchoolClass
from apps.core.models import AcademicYear, Term
from apps.examinations.models import Examination, ExaminationResult, ExaminationType
from apps.examinations.services import recompute_all, suspend_auto_compute
from apps.students.models import Student
from apps.subjects.models import ClassSubject, Subject


class Command(BaseCommand):
    help = (
        "Generates sample Midterm (out of 40) and End-of-term (out of 60) marks for every active student, "
        "then calculates each subject total, grade, overall average and class position. "
        "Safe to run again: existing exams are reused and marks are overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument("--class", dest="class_name", help="Only this class, e.g. 'Grade 7'. Default: every class with students.")
        parser.add_argument("--publish", action="store_true", help="Also publish the exams so students/parents can see them.")
        parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable marks.")

    def handle(self, *args, **opts):
        if opts["seed"] is not None:
            random.seed(opts["seed"])

        year = AcademicYear.objects.filter(is_current=True).first() or AcademicYear.objects.first()
        if not year:
            raise CommandError("Create an academic year first (run seed_initial_data).")
        term = Term.objects.filter(academic_year=year, is_current=True).first() or Term.objects.filter(academic_year=year).first()
        if not term:
            raise CommandError("Create a term first (run seed_initial_data).")

        midterm_type, _ = ExaminationType.objects.get_or_create(
            name="Midterm Exam", defaults={"category": "midterm", "weight_percentage": Decimal("40")}
        )
        end_type, _ = ExaminationType.objects.get_or_create(
            name="End of Term Exam", defaults={"category": "end_term", "weight_percentage": Decimal("60")}
        )
        plan = ((midterm_type, Decimal("40"), "Midterm"), (end_type, Decimal("60"), "End of Term"))

        classes = SchoolClass.objects.all()
        if opts["class_name"]:
            classes = classes.filter(name__iexact=opts["class_name"])
            if not classes:
                raise CommandError(f"No class named '{opts['class_name']}'.")

        marks_written = 0
        with suspend_auto_compute():
            for school_class in classes:
                students = list(Student.objects.filter(school_class=school_class, status="active"))
                if not students:
                    continue
                subjects = [cs.subject for cs in ClassSubject.objects.filter(school_class=school_class, academic_year=year).select_related("subject")]
                subjects = subjects or list(Subject.objects.all())

                for subject in subjects:
                    for exam_type, max_marks, label in plan:
                        exam, _ = Examination.objects.get_or_create(
                            school_class=school_class, subject=subject, examination_type=exam_type, term=term,
                            defaults={
                                "name": f"{term.get_name_display()} {label} - {subject.name}",
                                "academic_year": year, "date": term.start_date, "max_marks": max_marks,
                            },
                        )
                        if opts["publish"] and not exam.is_published:
                            exam.is_published = True
                            exam.marks_locked = True
                            exam.save()
                        for student in students:
                            score = (Decimal(random.randint(45, 98)) / 100 * exam.max_marks).quantize(Decimal("0.5"))
                            ExaminationResult.objects.update_or_create(
                                examination=exam, student=student, defaults={"marks_obtained": min(score, exam.max_marks)}
                            )
                            marks_written += 1

        groups = recompute_all()
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {marks_written} mark(s) and calculated results for {groups} subject group(s) in {term}."
        ))
