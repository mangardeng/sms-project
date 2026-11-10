from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrRegistrar, has_role
from apps.core.models import log_action
from apps.parents.models import Parent, ParentStudent
from apps.parents.serializers import ParentRegistrationSerializer, ParentSerializer, ParentStudentSerializer


class ParentViewSet(viewsets.ModelViewSet):
    """
    Admin/Registrar: full CRUD (register parents, link to students).
    Parent: may view/update only their OWN profile — never another
    parent's, and never a student directly (that's the students app,
    which itself is filtered by ParentStudent — see apps.parents.services).
    """

    queryset = Parent.objects.select_related("user").prefetch_related("student_links__student__user")
    search_fields = ["user__first_name", "user__last_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return ParentRegistrationSerializer
        return ParentSerializer

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdminOrRegistrar()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Parent.objects.select_related("user").prefetch_related("student_links__student__user")
        if has_role(user, User.Role.ADMIN, User.Role.REGISTRAR):
            return qs
        if user.role == User.Role.PARENT:
            return qs.filter(user=user)
        raise PermissionDenied("You do not have access to parent records.")

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="Parent", object_id=instance.id,
                    description="Registered parent and linked student(s)")

    def perform_update(self, serializer):
        target = self.get_object()
        user = self.request.user
        if user.role == User.Role.PARENT and target.user != user:
            raise PermissionDenied("You may only update your own profile.")
        instance = serializer.save()
        log_action(user=user, action="update", model_name="Parent", object_id=instance.id)


class ParentStudentLinkViewSet(viewsets.ModelViewSet):
    """
    Admin/Registrar-only management of the parent<->student relationship
    table. This is the table every other app's parent-access checks
    depend on (see apps.parents.services.parent_owns_student).
    """

    queryset = ParentStudent.objects.select_related("parent__user", "student__user")
    serializer_class = ParentStudentSerializer
    permission_classes = [IsAdminOrRegistrar]
    filterset_fields = ["parent", "student", "relationship"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user, action="create", model_name="ParentStudent", object_id=instance.id,
            description=f"Linked parent {instance.parent_id} to student {instance.student_id}",
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user, action="delete", model_name="ParentStudent", object_id=instance.id,
            description=f"Unlinked parent {instance.parent_id} from student {instance.student_id}",
        )
        instance.delete()
