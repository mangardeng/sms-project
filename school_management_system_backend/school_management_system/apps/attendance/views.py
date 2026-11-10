from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import has_role
from apps.attendance.models import Attendance
from apps.attendance.permissions import AttendanceAccessPermission
from apps.attendance.serializers import AttendanceSerializer, BulkAttendanceSerializer
from apps.core.models import log_action
from apps.parents.services import get_linked_student_ids
from apps.teachers.services import get_assigned_class_ids, teacher_assigned_to_class


class AttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [AttendanceAccessPermission]
    serializer_class = AttendanceSerializer
    filterset_fields = ["school_class", "student", "date", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = Attendance.objects.select_related("student__user", "school_class")

        if user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return qs

        if user.role == User.Role.TEACHER:
            return qs.filter(school_class_id__in=get_assigned_class_ids(user))

        if user.role == User.Role.PARENT:
            return qs.filter(student_id__in=get_linked_student_ids(user))

        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            return qs.filter(student=user.student_profile)

        return qs.none()

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="Attendance", object_id=instance.id)

    @action(detail=False, methods=["post"], url_path="bulk-record")
    def bulk_record(self, request):
        """
        POST /api/attendance/bulk-record/
        A teacher records attendance for their whole assigned class at once.
        """
        user = request.user
        school_class_id = request.data.get("school_class")

        if not (user.is_superuser or has_role(user, User.Role.ADMIN)):
            if user.role != User.Role.TEACHER or not teacher_assigned_to_class(user, int(school_class_id or 0)):
                raise PermissionDenied("You may only record attendance for classes assigned to you.")

        serializer = BulkAttendanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        records = serializer.save()

        log_action(
            user=user, action="create", model_name="Attendance",
            description=f"Bulk-recorded attendance for {len(records)} students in class {school_class_id}",
        )
        return Response(AttendanceSerializer(records, many=True).data)

    @action(detail=False, methods=["get"], url_path="class-summary")
    def class_summary(self, request):
        """GET /api/attendance/class-summary/?school_class=3&date=2026-09-05"""
        school_class_id = request.query_params.get("school_class")
        date = request.query_params.get("date")
        qs = self.get_queryset()
        if school_class_id:
            qs = qs.filter(school_class_id=school_class_id)
        if date:
            qs = qs.filter(date=date)

        summary = {
            "total": qs.count(),
            "present": qs.filter(status=Attendance.Status.PRESENT).count(),
            "absent": qs.filter(status=Attendance.Status.ABSENT).count(),
            "late": qs.filter(status=Attendance.Status.LATE).count(),
            "excused": qs.filter(status=Attendance.Status.EXCUSED).count(),
        }
        return Response(summary)
