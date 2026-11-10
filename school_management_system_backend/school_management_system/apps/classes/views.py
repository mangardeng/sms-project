from rest_framework import permissions, viewsets

from apps.accounts.permissions import IsAdmin
from apps.classes.models import SchoolClass, Stream
from apps.classes.serializers import SchoolClassSerializer, StreamSerializer
from apps.core.models import log_action


class IsAdminOrReadOnly(permissions.BasePermission):
    """Class/stream structure is managed by Admin only (3.4.1); everyone else can view (3.10.5)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return IsAdmin().has_permission(request, view)


class SchoolClassViewSet(viewsets.ModelViewSet):
    queryset = SchoolClass.objects.select_related("class_teacher__user").prefetch_related("streams").all()
    serializer_class = SchoolClassSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="SchoolClass", object_id=instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="update", model_name="SchoolClass", object_id=instance.id)

    def perform_destroy(self, instance):
        log_action(user=self.request.user, action="delete", model_name="SchoolClass", object_id=instance.id)
        instance.delete()


class StreamViewSet(viewsets.ModelViewSet):
    queryset = Stream.objects.select_related("school_class").all()
    serializer_class = StreamSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["school_class"]
