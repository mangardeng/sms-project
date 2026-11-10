from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, has_role
from apps.core.models import log_action
from apps.teachers.models import Teacher
from apps.teachers.serializers import TeacherRegistrationSerializer, TeacherSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD (register, update, deactivate).
    Head Teacher / Registrar / Admin: view all teachers.
    Teacher: view/update own profile only.
    """

    queryset = Teacher.objects.select_related("user").all()
    filterset_fields = ["is_active_staff"]
    search_fields = ["staff_id", "user__first_name", "user__last_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return TeacherRegistrationSerializer
        return TeacherSerializer

    def get_permissions(self):
        if self.action == "create" or self.action == "destroy":
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Teacher.objects.select_related("user")
        if has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return qs
        if user.role == User.Role.TEACHER:
            return qs.filter(user=user)
        raise PermissionDenied("You do not have access to teacher records.")

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="Teacher", object_id=instance.id,
                    description=f"Registered teacher {instance.staff_id}")

    def perform_update(self, serializer):
        target = self.get_object()
        user = self.request.user
        if user.role == User.Role.TEACHER and target.user != user:
            raise PermissionDenied("You may only update your own profile.")
        instance = serializer.save()
        log_action(user=user, action="update", model_name="Teacher", object_id=instance.id)


class MyTeacherProfileView(APIView):
    """GET /api/teachers/me/ — convenience endpoint for the logged-in teacher's own dashboard needs."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "teacher_profile"):
            raise PermissionDenied("You do not have a teacher profile.")
        return Response(TeacherSerializer(request.user.teacher_profile).data)
