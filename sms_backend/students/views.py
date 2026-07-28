from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions import IsAdmin
from .models import Student, StudentTransferLog
from .serializers import StudentSerializer, StudentTransferLogSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related("stream").prefetch_related("guardians")
    serializer_class = StudentSerializer
    permission_classes = [IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name", "admission_number"]

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        """POST /api/students/students/{id}/promote/  body: {"to_stream": <id>, "reason": "..."}"""
        student = self.get_object()
        to_stream_id = request.data.get("to_stream")
        reason = request.data.get("reason", "")

        StudentTransferLog.objects.create(
            student=student,
            from_stream=student.stream,
            to_stream_id=to_stream_id,
            reason=reason,
        )
        student.stream_id = to_stream_id
        student.save()
        return Response(StudentSerializer(student).data)