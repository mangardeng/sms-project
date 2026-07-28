from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from core.permissions import IsTeacher, IsAdmin
from .models import StudentAttendance, TeacherAttendance
from .serializers import StudentAttendanceSerializer, TeacherAttendanceSerializer
from django.db.models import Count



class StudentAttendanceViewSet(viewsets.ModelViewSet):
    queryset = StudentAttendance.objects.select_related("student", "school_class").all()
    serializer_class = StudentAttendanceSerializer
    permission_classes = [IsTeacher | IsAdmin]
    filterset_fields = ["school_class", "date", "student"]

    @action(detail=False, methods=["post"])
    def bulk_mark(self, request):
        """
        POST /api/attendance/students/bulk_mark/
        body: {
          "school_class": 3, "date": "2026-07-28",
          "entries": [{"student": 12, "status": "PRESENT"}, {"student": 13, "status": "ABSENT"}]
        }
        """
        school_class = request.data.get("school_class")
        date = request.data.get("date")
        entries = request.data.get("entries", [])

        if not (school_class and date and entries):
            raise ValidationError("school_class, date, and entries are all required.")

        created, updated = 0, 0
        with transaction.atomic():
            for entry in entries:
                obj, was_created = StudentAttendance.objects.update_or_create(
                    student_id=entry["student"], date=date,
                    defaults={
                        "school_class_id": school_class,
                        "status": entry["status"],
                        "recorded_by": request.user,
                    },
                )
                created += was_created
                updated += not was_created

        return Response({"created": created, "updated": updated})
    @action(detail=False, methods=["get"])
    def monthly_summary(self, request):
        """
        GET /api/attendance/students/monthly_summary/?student=12&year=2026&month=7
        Returns present/absent/late/excused counts and a percentage for that student+month.
        """
        student_id = request.query_params.get("student")
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        qs = StudentAttendance.objects.filter(
            student_id=student_id, date__year=year, date__month=month
        )
        total = qs.count()
        if total == 0:
            return Response({"total": 0, "percentage": None})

        present = qs.filter(status="PRESENT").count()
        breakdown = qs.values("status").annotate(count=Count("id"))

        return Response({
            "total": total,
            "present": present,
            "percentage": round((present / total) * 100, 1),
            "breakdown": list(breakdown),
        })

class TeacherAttendanceViewSet(viewsets.ModelViewSet):
    queryset = TeacherAttendance.objects.select_related("teacher").all()
    serializer_class = TeacherAttendanceSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["teacher", "date"]