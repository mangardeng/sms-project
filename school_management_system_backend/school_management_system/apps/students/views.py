from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrRegistrar, has_role
from apps.core.models import log_action
from apps.parents.services import get_linked_student_ids
from apps.students.models import Student
from apps.students.permissions import StudentAccessPermission
from apps.students.serializers import (
    StudentRegistrationSerializer,
    StudentSerializer,
    StudentTransferHistorySerializer,
    StudentTransferSerializer,
)
from apps.teachers.services import get_assigned_class_ids


class StudentViewSet(viewsets.ModelViewSet):
    """
    Role-scoped student management. See apps.students.permissions for
    the full access matrix and apps.parents.services for the
    parent/student relationship enforcement (design doc 3.14).
    """

    permission_classes = [StudentAccessPermission]
    filterset_fields = ["school_class", "stream", "status"]
    search_fields = ["index_number", "user__first_name", "user__last_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return StudentRegistrationSerializer
        if self.action == "transfer":
            return StudentTransferSerializer
        return StudentSerializer

    def get_queryset(self):
        """
        This is the primary defense described in 3.14: rather than
        returning every student and hoping has_object_permission saves
        us, we narrow the queryset itself so a parent/teacher/student
        can never even see other students in a list call, and a
        direct-by-id request for a record outside their scope returns
        404 (via get_object_or_404 semantics) instead of leaking
        existence of the record.
        """
        user = self.request.user
        qs = Student.objects.select_related("user", "school_class", "stream")

        if user.is_superuser or has_role(
            user, User.Role.ADMIN, 
            User.Role.REGISTRAR, 
            User.Role.HEAD_TEACHER, 
            User.Role.ACCOUNTANT,):
            return qs

        if user.role == User.Role.TEACHER:
            return qs.filter(school_class_id__in=get_assigned_class_ids(user))

        if user.role == User.Role.PARENT:
            return qs.filter(id__in=get_linked_student_ids(user))

        if user.role == User.Role.STUDENT:
            return qs.filter(user=user)

        return qs.none()

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user, action="create", model_name="Student", object_id=instance.id,
            description=f"Registered student {instance.index_number}",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="Student", object_id=instance.id)

    def perform_destroy(self, instance):
        log_action(user=self.request.user, action="delete", model_name="Student", object_id=instance.id)
        instance.delete()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "transfer"):
            return [IsAdminOrRegistrar()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """POST /api/students/{id}/transfer/  {"to_class": <id>, "reason": "..."}"""
        student = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"student": student, "request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            user=request.user, action="update", model_name="Student", object_id=student.id,
            description="Student transferred to a new class",
        )
        return Response(StudentSerializer(student).data)

    @action(detail=True, methods=["get"], url_path="transfer-history")
    def transfer_history(self, request, pk=None):
        student = self.get_object()
        history = student.transfer_history.all()
        return Response(StudentTransferHistorySerializer(history, many=True).data)


class MyStudentProfileView(viewsets.ViewSet):
    """GET /api/students/me/ — convenience endpoint for the logged-in student's own dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if not hasattr(request.user, "student_profile"):
            raise PermissionDenied("You do not have a student profile.")
        return Response(StudentSerializer(request.user.student_profile).data)
