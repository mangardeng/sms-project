"""
Role-based dashboard statistics (design doc 4.8).

No new models are needed here — this app only aggregates data that
already lives in the other apps. Every helper re-applies the SAME
access rules used elsewhere (parent_owns_student, teacher assigned
classes, etc.) so the dashboard can never leak more than the
underlying resource endpoints already allow.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.attendance.models import Attendance
from apps.classes.models import SchoolClass
from apps.examinations.models import ExaminationResult
from apps.fees.models import Payment, student_balance
from apps.library.models import Book, BorrowingRecord
from apps.notifications.models import Notification
from apps.parents.services import get_linked_student_ids
from apps.students.models import Student
from apps.subjects.models import ClassSubject
from apps.teachers.models import Teacher
from apps.teachers.services import get_assigned_class_ids


class DashboardView(APIView):
    """GET /api/dashboard/ — returns a payload shaped for the caller's role."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        handler = {
            User.Role.ADMIN: self._admin,
            User.Role.HEAD_TEACHER: self._head_teacher,
            User.Role.REGISTRAR: self._registrar,
            User.Role.TEACHER: self._teacher,
            User.Role.ACCOUNTANT: self._accountant,
            User.Role.LIBRARIAN: self._librarian,
            User.Role.PARENT: self._parent,
            User.Role.STUDENT: self._student,
        }.get(user.role)

        if handler is None:
            return Response({"detail": "No dashboard configured for this role."}, status=400)

        return Response(handler(user))

    # ------------------------------------------------------------------
    def _recent_notifications(self, user, limit=5):
        from apps.notifications.serializers import NotificationSerializer

        qs = Notification.objects.filter(recipient=user).order_by("-created_at")[:limit]
        return NotificationSerializer(qs, many=True).data

    def _admin(self, user):
        today = timezone.now().date()
        return {
            "total_students": Student.objects.filter(status=Student.Status.ACTIVE).count(),
            "total_teachers": Teacher.objects.filter(is_active_staff=True).count(),
            "total_parents": User.objects.filter(role=User.Role.PARENT, is_active=True).count(),
            "total_classes": SchoolClass.objects.filter(is_active=True).count(),
            "fee_collection_this_month": float(
                sum(
                    p.amount_paid
                    for p in Payment.objects.filter(is_void=False, payment_date__year=today.year, payment_date__month=today.month)
                )
            ),
            "attendance_today": self._attendance_breakdown(Attendance.objects.filter(date=today)),
            "examinations_pending_publish": self._exam_stats(),
            "recent_activities": self._recent_audit_log(),
            "notifications": self._recent_notifications(user),
        }

    def _head_teacher(self, user):
        today = timezone.now().date()
        return {
            "total_students": Student.objects.filter(status=Student.Status.ACTIVE).count(),
            "total_teachers": Teacher.objects.filter(is_active_staff=True).count(),
            "attendance_today": self._attendance_breakdown(Attendance.objects.filter(date=today)),
            "average_exam_percentage": self._average_percentage(ExaminationResult.objects.filter(examination__is_published=True)),
            "fee_collection_this_month": float(
                sum(
                    p.amount_paid
                    for p in Payment.objects.filter(is_void=False, payment_date__year=today.year, payment_date__month=today.month)
                )
            ),
            "notifications": self._recent_notifications(user),
        }

    def _registrar(self, user):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        by_class = (
            Student.objects.filter(status=Student.Status.ACTIVE)
            .values("school_class__name")
            .order_by("school_class__name")
        )
        counts = {}
        for row in by_class:
            name = row["school_class__name"] or "Unassigned"
            counts[name] = counts.get(name, 0) + 1

        return {
            "total_active_students": Student.objects.filter(status=Student.Status.ACTIVE).count(),
            "students_by_class": counts,
            "recent_registrations": Student.objects.filter(created_at__gte=thirty_days_ago).count(),
        }

    def _teacher(self, user):
        if not hasattr(user, "teacher_profile"):
            return {"detail": "No teacher profile linked to this account."}

        class_ids = get_assigned_class_ids(user)
        today = timezone.now().date()
        return {
            "assigned_classes": list(SchoolClass.objects.filter(id__in=class_ids).values("id", "name")),
            "assigned_subjects": list(
                ClassSubject.objects.filter(teacher=user.teacher_profile).values(
                    "subject__id", "subject__name", "school_class__name"
                )
            ),
            "total_students_taught": Student.objects.filter(school_class_id__in=class_ids, status=Student.Status.ACTIVE).count(),
            "attendance_today": self._attendance_breakdown(Attendance.objects.filter(school_class_id__in=class_ids, date=today)),
            "notifications": self._recent_notifications(user),
        }

    def _accountant(self, user):
        today = timezone.now().date()
        recent_payments = Payment.objects.filter(is_void=False).select_related("student__user").order_by("-created_at")[:10]
        return {
            "total_collected_this_month": float(
                sum(
                    p.amount_paid
                    for p in Payment.objects.filter(is_void=False, payment_date__year=today.year, payment_date__month=today.month)
                )
            ),
            "total_collected_all_time": float(sum(p.amount_paid for p in Payment.objects.filter(is_void=False))),
            "recent_payments": [
                {
                    "receipt_number": p.receipt_number,
                    "student": p.student.index_number,
                    "amount": float(p.amount_paid),
                    "date": p.payment_date,
                }
                for p in recent_payments
            ],
        }

    def _librarian(self, user):
        today = timezone.now().date()
        return {
            "total_books": Book.objects.count(),
            "available_books": sum(b.available_copies for b in Book.objects.all()),
            "borrowed_books": BorrowingRecord.objects.filter(status=BorrowingRecord.Status.BORROWED).count(),
            "overdue_books": BorrowingRecord.objects.filter(status=BorrowingRecord.Status.BORROWED, due_date__lt=today).count(),
            "outstanding_fines": float(
                sum(r.fine_amount for r in BorrowingRecord.objects.exclude(fine_amount=0))
            ),
        }

    def _parent(self, user):
        student_ids = get_linked_student_ids(user)
        students = Student.objects.filter(id__in=student_ids).select_related("user", "school_class")

        children = []
        for student in students:
            attendance_qs = Attendance.objects.filter(student=student)
            children.append(
                {
                    "id": student.id,
                    "name": student.user.get_full_name(),
                    "index_number": student.index_number,
                    "school_class": student.school_class.name if student.school_class else None,
                    "attendance_summary": self._attendance_breakdown(attendance_qs),
                    "average_exam_percentage": self._average_percentage(
                        ExaminationResult.objects.filter(student=student, examination__is_published=True)
                    ),
                    "fee_balance": float(student_balance(student)),
                }
            )

        return {"children": children, "notifications": self._recent_notifications(user)}

    def _student(self, user):
        if not hasattr(user, "student_profile"):
            return {"detail": "No student profile linked to this account."}

        student = user.student_profile
        attendance_qs = Attendance.objects.filter(student=student)
        results = ExaminationResult.objects.filter(student=student, examination__is_published=True).select_related(
            "examination__subject"
        )

        return {
            "profile": {
                "index_number": student.index_number,
                "name": student.user.get_full_name(),
                "school_class": student.school_class.name if student.school_class else None,
                "stream": student.stream.name if student.stream else None,
            },
            "attendance_summary": self._attendance_breakdown(attendance_qs),
            "recent_results": [
                {
                    "subject": r.examination.subject.name,
                    "examination": r.examination.name,
                    "marks_obtained": float(r.marks_obtained),
                    "grade": r.grade,
                }
                for r in results.order_by("-created_at")[:10]
            ],
            "fee_balance": float(student_balance(student)),
            "notifications": self._recent_notifications(user),
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _attendance_breakdown(queryset):
        return {
            "total": queryset.count(),
            "present": queryset.filter(status=Attendance.Status.PRESENT).count(),
            "absent": queryset.filter(status=Attendance.Status.ABSENT).count(),
            "late": queryset.filter(status=Attendance.Status.LATE).count(),
            "excused": queryset.filter(status=Attendance.Status.EXCUSED).count(),
        }

    @staticmethod
    def _average_percentage(results_queryset):
        results = list(results_queryset.select_related("examination"))
        if not results:
            return None
        total_pct = 0
        counted = 0
        for r in results:
            if r.examination.max_marks:
                total_pct += float(r.marks_obtained) / float(r.examination.max_marks) * 100
                counted += 1
        return round(total_pct / counted, 2) if counted else None

    @staticmethod
    def _exam_stats():
        from apps.examinations.models import Examination

        return {
            "total": Examination.objects.count(),
            "published": Examination.objects.filter(is_published=True).count(),
            "unpublished": Examination.objects.filter(is_published=False).count(),
        }

    @staticmethod
    def _recent_audit_log(limit=10):
        from apps.core.models import AuditLog

        return [
            {
                "user": str(entry.user) if entry.user else "System",
                "action": entry.action,
                "model_name": entry.model_name,
                "description": entry.description,
                "timestamp": entry.timestamp,
            }
            for entry in AuditLog.objects.order_by("-timestamp")[:limit]
        ]
