"""
Seeds a realistic demo dataset through the ACTUAL model layer (the same
code paths the API uses), so the system has something to log in to and
click around immediately after `migrate`.

Safe to re-run: every object is created with get_or_create keyed on a
natural unique field (username, staff_id, index-generating Student
save(), etc.), so running this twice will not create duplicates for
users/teachers/classes/subjects, though it WILL add a fresh day of
attendance each run (harmless — unique_together just skips days already
recorded).

Usage:
    python manage.py seed_demo_data
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.classes.models import SchoolClass, Stream
from apps.core.models import AcademicYear, Term
from apps.examinations.models import Examination, ExaminationResult, ExaminationType
from apps.fees.models import FeeStructure, Payment
from apps.library.models import Book, BorrowingRecord
from apps.notifications.models import Notification
from apps.parents.models import Parent, ParentStudent
from apps.students.models import Student
from apps.subjects.models import ClassSubject, Subject
from apps.teachers.models import Teacher

User = get_user_model()
DEMO_PASSWORD = "Password@123"


class Command(BaseCommand):
    help = "Populates the database with a realistic demo school (classes, subjects, teachers, students, parents, attendance, exams, fees, library, notifications)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        year, term = self._academic_period()
        classes = self._classes(year)
        subjects = self._subjects()
        teachers = self._teachers()
        self._assign_subjects(classes, subjects, teachers, year)
        students = self._students(classes)
        self._parents(students)
        self._staff_accounts()
        self._attendance(students, teachers)
        self._examinations(classes, subjects, teachers, year, term, students)
        self._fees(classes, term)
        self._library(students, teachers)
        self._notifications(students)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully."))
        self.stdout.write(self.style.WARNING(f"All demo accounts use the password: {DEMO_PASSWORD}"))
        self._print_login_summary()

    # ------------------------------------------------------------------
    def _academic_period(self):
        year, _ = AcademicYear.objects.get_or_create(
            name="2025/2026",
            defaults={"start_date": date(2025, 9, 1), "end_date": date(2026, 7, 31), "is_current": True},
        )
        term, _ = Term.objects.get_or_create(
            academic_year=year,
            name=Term.TermName.TERM_1,
            defaults={"start_date": date(2025, 9, 1), "end_date": date(2025, 12, 15), "is_current": True},
        )
        self.stdout.write(f"  Academic year/term: {year} / {term}")
        return year, term

    def _classes(self, year):
        grade7, _ = SchoolClass.objects.get_or_create(name="Grade 7", defaults={"level": 7})
        grade8, _ = SchoolClass.objects.get_or_create(name="Grade 8", defaults={"level": 8})

        g7a, _ = Stream.objects.get_or_create(school_class=grade7, name="A", defaults={"capacity": 40})
        g7b, _ = Stream.objects.get_or_create(school_class=grade7, name="B", defaults={"capacity": 40})
        g8a, _ = Stream.objects.get_or_create(school_class=grade8, name="A", defaults={"capacity": 40})

        self.stdout.write(f"  Classes: {grade7}, {grade8} (streams: {g7a}, {g7b}, {g8a})")
        return {"grade7": grade7, "grade8": grade8, "g7a": g7a, "g7b": g7b, "g8a": g8a}

    def _subjects(self):
        data = [
            ("MATH101", "Mathematics"),
            ("ENG101", "English"),
            ("SCI101", "Science"),
            ("SST101", "Social Studies"),
            ("ICT101", "Computer Studies"),
        ]
        subjects = {}
        for code, name in data:
            subject, _ = Subject.objects.get_or_create(code=code, defaults={"name": name, "is_compulsory": True})
            subjects[code] = subject
        self.stdout.write(f"  Subjects: {', '.join(s.name for s in subjects.values())}")
        return subjects

    def _make_user(self, username, first_name, last_name, role, email=None):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email or f"{username}@school.example",
                "role": role,
                "must_change_password": False,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _teachers(self):
        specs = [
            ("teacher.mary", "Mary", "Achieng", "TCH0001", Teacher.Gender.FEMALE),
            ("teacher.john", "John", "Otieno", "TCH0002", Teacher.Gender.MALE),
            ("teacher.grace", "Grace", "Nyambura", "TCH0003", Teacher.Gender.FEMALE),
        ]
        teachers = {}
        for username, first, last, staff_id, gender in specs:
            user = self._make_user(username, first, last, User.Role.TEACHER)
            teacher, _ = Teacher.objects.get_or_create(
                user=user,
                defaults={
                    "staff_id": staff_id,
                    "gender": gender,
                    "date_employed": date(2022, 1, 10),
                    "qualification": "Bachelor of Education",
                },
            )
            teachers[staff_id] = teacher
        self.stdout.write(f"  Teachers: {', '.join(t.user.get_full_name() for t in teachers.values())}")
        return teachers

    def _assign_subjects(self, classes, subjects, teachers, year):
        grade7, grade8 = classes["grade7"], classes["grade8"]
        mary, john, grace = teachers["TCH0001"], teachers["TCH0002"], teachers["TCH0003"]

        grade7.class_teacher = john
        grade7.save(update_fields=["class_teacher"])
        grade8.class_teacher = grace
        grade8.save(update_fields=["class_teacher"])

        assignments = [
            (grade7, subjects["MATH101"], mary),
            (grade7, subjects["SCI101"], mary),
            (grade7, subjects["ENG101"], john),
            (grade7, subjects["SST101"], john),
            (grade7, subjects["ICT101"], mary),
            (grade8, subjects["MATH101"], grace),
            (grade8, subjects["ENG101"], grace),
            (grade8, subjects["SCI101"], grace),
        ]
        for school_class, subject, teacher in assignments:
            ClassSubject.objects.get_or_create(
                school_class=school_class, subject=subject, academic_year=year, defaults={"teacher": teacher}
            )
        self.stdout.write("  Class/subject/teacher assignments created.")

    def _students(self, classes):
        specs = [
            ("Brian", "Kiptoo", classes["g7a"], classes["grade7"], "male", date(2013, 4, 12)),
            ("Faith", "Wambui", classes["g7a"], classes["grade7"], "female", date(2013, 6, 2)),
            ("Kevin", "Omondi", classes["g7a"], classes["grade7"], "male", date(2013, 1, 20)),
            ("Diana", "Chebet", classes["g7a"], classes["grade7"], "female", date(2013, 9, 15)),
            ("Samuel", "Mwangi", classes["g7b"], classes["grade7"], "male", date(2013, 3, 5)),
            ("Esther", "Naliaka", classes["g7b"], classes["grade7"], "female", date(2013, 11, 30)),
            ("Peter", "Kimani", classes["g8a"], classes["grade8"], "male", date(2012, 2, 18)),
            ("Ann", "Njeri", classes["g8a"], classes["grade8"], "female", date(2012, 7, 22)),
        ]
        students = []
        for first, last, stream, school_class, gender, dob in specs:
            username = f"std.{first.lower()}.{last.lower()}"
            user = self._make_user(username, first, last, User.Role.STUDENT)
            student, created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "school_class": school_class,
                    "stream": stream,
                    "gender": gender,
                    "date_of_birth": dob,
                    "status": Student.Status.ACTIVE,
                    "emergency_contact_name": f"{last} Family",
                    "emergency_contact_phone": "+254700000000",
                },
            )
            students.append(student)
        self.stdout.write(
            "  Students: " + ", ".join(f"{s.user.get_full_name()} ({s.index_number})" for s in students)
        )
        return students

    def _parents(self, students):
        pairs = [
            ("parent.kiptoo", "Robert", "Kiptoo", [students[0]], ParentStudent.Relationship.FATHER),
            ("parent.wambui", "Lucy", "Wambui", [students[1]], ParentStudent.Relationship.MOTHER),
            ("parent.omondi", "James", "Omondi", [students[2], students[3]], ParentStudent.Relationship.FATHER),
            ("parent.mwangi", "Susan", "Mwangi", [students[4]], ParentStudent.Relationship.MOTHER),
            ("parent.kimani", "Daniel", "Kimani", [students[6], students[7]], ParentStudent.Relationship.FATHER),
        ]
        for username, first, last, kids, relationship in pairs:
            user = self._make_user(username, first, last, User.Role.PARENT)
            parent, _ = Parent.objects.get_or_create(user=user, defaults={"occupation": "N/A"})
            for kid in kids:
                ParentStudent.objects.get_or_create(
                    parent=parent, student=kid, defaults={"relationship": relationship, "is_primary_contact": True}
                )
        self.stdout.write("  Parents created and linked to their children.")

    def _staff_accounts(self):
        self._make_user("admin.demo", "Admin", "Demo", User.Role.ADMIN)
        admin_user = User.objects.get(username="admin.demo")
        if not admin_user.is_staff:
            admin_user.is_staff = True
            admin_user.save(update_fields=["is_staff"])

        self._make_user("headteacher1", "Rose", "Atieno", User.Role.HEAD_TEACHER)
        self._make_user("registrar1", "Michael", "Ouma", User.Role.REGISTRAR)
        self._make_user("accountant1", "Nancy", "Wanjiku", User.Role.ACCOUNTANT)
        self._make_user("librarian1", "Joseph", "Kariuki", User.Role.LIBRARIAN)
        self.stdout.write("  Staff accounts: admin.demo, headteacher1, registrar1, accountant1, librarian1")

    def _attendance(self, students, teachers):
        john = teachers["TCH0002"].user
        today = timezone.now().date()
        days = [today - timedelta(days=i) for i in range(5) if (today - timedelta(days=i)).weekday() < 5]

        statuses = [Attendance.Status.PRESENT] * 8 + [Attendance.Status.LATE, Attendance.Status.ABSENT]
        count = 0
        for day in days:
            for student in students:
                _, created = Attendance.objects.get_or_create(
                    student=student,
                    date=day,
                    defaults={
                        "school_class": student.school_class,
                        "status": random.choice(statuses),
                        "recorded_by": john,
                    },
                )
                if created:
                    count += 1
        self.stdout.write(f"  Attendance: {count} new records across {len(days)} school day(s).")

    def _examinations(self, classes, subjects, teachers, year, term, students):
        exam_type, _ = ExaminationType.objects.get_or_create(
            name="Midterm Exam", defaults={"category": "midterm", "weight_percentage": Decimal("40.00")}
        )
        ExaminationType.objects.get_or_create(
            name="End of Term Exam", defaults={"category": "end_term", "weight_percentage": Decimal("60.00")}
        )
        mary = teachers["TCH0001"]
        grace = teachers["TCH0003"]

        exam_g7_math, _ = Examination.objects.get_or_create(
            school_class=classes["grade7"], subject=subjects["MATH101"], examination_type=exam_type, term=term,
            defaults={
                "name": "Term 1 Midterm - Mathematics", "academic_year": year,
                "date": timezone.now().date() - timedelta(days=3), "max_marks": Decimal("100.00"),
                "is_published": True, "marks_locked": True, "created_by": mary.user,
            },
        )
        exam_g8_math, _ = Examination.objects.get_or_create(
            school_class=classes["grade8"], subject=subjects["MATH101"], examination_type=exam_type, term=term,
            defaults={
                "name": "Term 1 Midterm - Mathematics", "academic_year": year,
                "date": timezone.now().date() - timedelta(days=3), "max_marks": Decimal("100.00"),
                "is_published": True, "marks_locked": True, "created_by": grace.user,
            },
        )

        g7_students = [s for s in students if s.school_class == classes["grade7"]]
        g8_students = [s for s in students if s.school_class == classes["grade8"]]

        count = 0
        for student in g7_students:
            _, created = ExaminationResult.objects.get_or_create(
                examination=exam_g7_math, student=student,
                defaults={"marks_obtained": Decimal(random.randint(45, 98)), "entered_by": mary.user},
            )
            count += created
        for student in g8_students:
            _, created = ExaminationResult.objects.get_or_create(
                examination=exam_g8_math, student=student,
                defaults={"marks_obtained": Decimal(random.randint(45, 98)), "entered_by": grace.user},
            )
            count += created

        self.stdout.write(f"  Examinations: 2 midterm exams created, {count} result(s) entered and published.")

    def _fees(self, classes, term):
        accountant = User.objects.get(username="accountant1")
        structures = {}
        for school_class in (classes["grade7"], classes["grade8"]):
            structure, _ = FeeStructure.objects.get_or_create(
                school_class=school_class, term=term, name="Tuition Fee",
                defaults={"amount": Decimal("50000.00"), "created_by": accountant},
            )
            structures[school_class.id] = structure

        # A handful of partial payments so /api/fees/balance/ has something to show.
        sample_students = list(classes["grade7"].students.all()[:2]) + list(classes["grade8"].students.all()[:1])
        count = 0
        for student in sample_students:
            structure = structures[student.school_class_id]
            payment, created = Payment.objects.get_or_create(
                student=student, fee_structure=structure, amount_paid=Decimal("20000.00"),
                defaults={"method": Payment.Method.MOBILE_MONEY, "recorded_by": accountant, "notes": "Term 1 first installment"},
            )
            count += created
        self.stdout.write(f"  Fees: 2 fee structures, {count} demo payment(s) recorded.")

    def _library(self, students, teachers):
        books_data = [
            ("Things Fall Apart", "Chinua Achebe", "9780435905250", "Literature", 3),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", "Science", 2),
            ("Introduction to Algorithms", "Cormen et al.", "9780262033848", "Computer Studies", 2),
            ("The River and the Source", "Margaret Ogola", "9789966465808", "Literature", 4),
            ("Longman Mathematics", "Longman", "9780582123456", "Mathematics", 5),
        ]
        librarian = User.objects.get(username="librarian1")
        books = []
        for title, author, isbn, category, copies in books_data:
            book, _ = Book.objects.get_or_create(
                isbn=isbn, defaults={"title": title, "author": author, "category": category,
                                      "total_copies": copies, "available_copies": copies},
            )
            books.append(book)

        count = 0
        if books and students:
            record, created = BorrowingRecord.objects.get_or_create(
                book=books[0], student=students[0],
                defaults={"due_date": timezone.now().date() + timedelta(days=14), "issued_by": librarian},
            )
            if created:
                books[0].available_copies = max(books[0].available_copies - 1, 0)
                books[0].save(update_fields=["available_copies"])
                count += 1

            overdue_record, created = BorrowingRecord.objects.get_or_create(
                book=books[1], student=students[1],
                defaults={"due_date": timezone.now().date() - timedelta(days=5), "issued_by": librarian},
            )
            if created:
                books[1].available_copies = max(books[1].available_copies - 1, 0)
                books[1].save(update_fields=["available_copies"])
                count += 1

        self.stdout.write(f"  Library: {len(books)} books, {count} new borrowing record(s) (one overdue).")

    def _notifications(self, students):
        admin_user = User.objects.get(username="admin.demo")

        for user in User.objects.filter(is_active=True):
            Notification.objects.get_or_create(
                recipient=user, title="Welcome to Term 1, 2025/2026",
                defaults={
                    "category": Notification.Category.ANNOUNCEMENT, "is_broadcast": True,
                    "message": "Welcome back! Term 1 begins on 1st September. Please check your dashboard for your class and subject details.",
                    "created_by": admin_user,
                },
            )

        if students:
            first_parent_link = students[0].parent_links.first()
            if first_parent_link:
                Notification.objects.get_or_create(
                    recipient=first_parent_link.parent.user, title="Fee balance reminder",
                    defaults={
                        "category": Notification.Category.FEE_REMINDER,
                        "message": f"A balance remains on {students[0].user.get_full_name()}'s Term 1 tuition fee. Please clear it at your earliest convenience.",
                        "created_by": admin_user,
                    },
                )
        self.stdout.write("  Notifications: welcome announcement broadcast + a sample fee reminder.")

    def _print_login_summary(self):
        self.stdout.write("\nDemo accounts you can log in with (POST /api/auth/login/):")
        self.stdout.write("  Admin          -> username: admin.demo        password: " + DEMO_PASSWORD)
        self.stdout.write("  Head Teacher   -> username: headteacher1      password: " + DEMO_PASSWORD)
        self.stdout.write("  Registrar      -> username: registrar1        password: " + DEMO_PASSWORD)
        self.stdout.write("  Accountant     -> username: accountant1       password: " + DEMO_PASSWORD)
        self.stdout.write("  Librarian      -> username: librarian1        password: " + DEMO_PASSWORD)
        self.stdout.write("  Teacher        -> username: teacher.john      password: " + DEMO_PASSWORD)
        self.stdout.write("  Parent         -> username: parent.kiptoo     password: " + DEMO_PASSWORD)
        self.stdout.write("  Student        -> use the printed index number (e.g. STD00001) password: " + DEMO_PASSWORD)
        self.stdout.write("\nRun `python manage.py shell -c \"from apps.students.models import Student; "
                            "[print(s.index_number, s.user.get_full_name()) for s in Student.objects.all()]\"` "
                            "to list every student's login index number.")
