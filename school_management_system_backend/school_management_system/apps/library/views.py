from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import has_role
from apps.core.models import log_action
from apps.library.models import Book, BorrowingRecord
from apps.library.permissions import LibraryAccessPermission
from apps.library.serializers import BookSerializer, BorrowingRecordSerializer
from apps.parents.services import get_linked_student_ids


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [LibraryAccessPermission]
    search_fields = ["title", "author", "isbn", "category"]
    filterset_fields = ["category"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(user=self.request.user, action="create", model_name="Book", object_id=instance.id)


class BorrowingRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [LibraryAccessPermission]
    serializer_class = BorrowingRecordSerializer
    filterset_fields = ["book", "student", "teacher", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = BorrowingRecord.objects.select_related("book", "student__user", "teacher__user")

        if user.is_superuser or has_role(
            user, User.Role.ADMIN, User.Role.LIBRARIAN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR, User.Role.TEACHER
        ):
            return qs
        if user.role == User.Role.PARENT:
            return qs.filter(student_id__in=get_linked_student_ids(user))
        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            return qs.filter(student=user.student_profile)
        return qs.none()

    def perform_create(self, serializer):
        instance = serializer.save(issued_by=self.request.user)
        log_action(user=self.request.user, action="create", model_name="BorrowingRecord", object_id=instance.id)

    @action(detail=True, methods=["post"])
    def mark_returned(self, request, pk=None):
        record = self.get_object()
        record.mark_returned()
        log_action(user=request.user, action="update", model_name="BorrowingRecord", object_id=record.id, description="Book returned")
        return Response(BorrowingRecordSerializer(record).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        from django.utils import timezone

        qs = self.get_queryset().filter(status="borrowed", due_date__lt=timezone.now().date())
        return Response(BorrowingRecordSerializer(qs, many=True).data)
