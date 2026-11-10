from rest_framework import permissions, viewsets

from apps.accounts.models import User
from apps.classes.views import IsAdminOrReadOnly
from apps.core.models import log_action
from apps.subjects.models import ClassSubject, Subject
from apps.subjects.serializers import ClassSubjectSerializer, SubjectSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    """Subject management (3.4.1 Admin: 'Manage subjects'; 3.10.6)."""

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name", "code"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="Subject", object_id=instance.id)


class ClassSubjectViewSet(viewsets.ModelViewSet):
    """
    Assigns subjects (and a teacher) to a class. Teachers may only VIEW
    their own assignments; only Admin manages the assignments themselves.
    """

    serializer_class = ClassSubjectSerializer
    filterset_fields = ["school_class", "subject", "teacher", "academic_year"]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdminOrReadOnly()]

    def get_queryset(self):
        qs = ClassSubject.objects.select_related("school_class", "subject", "teacher__user")
        user = self.request.user
        if user.role == User.Role.TEACHER and hasattr(user, "teacher_profile"):
            return qs.filter(teacher=user.teacher_profile)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="ClassSubject", object_id=instance.id)
