from rest_framework import viewsets
from core.permissions import IsAdmin
from .models import Teacher, SubjectAllocation
from .serializers import TeacherSerializer, SubjectAllocationSerializer

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.select_related("user").prefetch_related("allocations")
    serializer_class = TeacherSerializer
    permission_classes = [IsAdmin]

class SubjectAllocationViewSet(viewsets.ModelViewSet):
    queryset = SubjectAllocation.objects.all()
    serializer_class = SubjectAllocationSerializer
    permission_classes = [IsAdmin]