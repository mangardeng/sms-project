from rest_framework import permissions, viewsets

from apps.accounts.permissions import IsAdmin
from apps.core.models import AcademicYear, Term, log_action
from apps.core.serializers import AcademicYearSerializer, TermSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Academic years/terms are school-wide calendar structure: any
    authenticated user may read them (needed to populate dropdowns
    across the app), but only an Administrator may create or change
    them (3.4.1 'Configure academic years and terms').
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return IsAdmin().has_permission(request, view)


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="AcademicYear", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="AcademicYear", object_id=instance.id)


class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.select_related("academic_year").all()
    serializer_class = TermSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["academic_year", "is_current"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="Term", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="Term", object_id=instance.id)
