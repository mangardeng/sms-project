from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdmin

from .models import (
    AcademicYear,
    SchoolClass,
    Stream,
    TimetableEntry
)

from .serializers import (
    AcademicYearSerializer,
    SchoolClassSerializer,
    StreamSerializer,
    TimetableEntrySerializer
)



class AcademicYearViewSet(viewsets.ModelViewSet):

    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAdmin]



class SchoolClassViewSet(viewsets.ModelViewSet):

    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer
    permission_classes = [IsAdmin]



class StreamViewSet(viewsets.ModelViewSet):

    queryset = Stream.objects.all()
    serializer_class = StreamSerializer
    permission_classes = [IsAdmin]



class TimetableEntryViewSet(viewsets.ModelViewSet):

    queryset = TimetableEntry.objects.all()
    serializer_class = TimetableEntrySerializer
    permission_classes = [IsAdmin]


    @action(detail=False, methods=["get"])
    def by_stream(self, request):

        stream_id = request.query_params.get("stream")


        entries = TimetableEntry.objects.filter(
            stream_id=stream_id
        ).select_related(
            "time_slot",
            "teacher"
        )


        serializer = TimetableEntrySerializer(
            entries,
            many=True
        )


        return Response(serializer.data)