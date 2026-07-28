from rest_framework import serializers
from .models import AcademicYear, SchoolClass, Stream, TimeSlot,TimetableEntry

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"

class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = "__all__"

class SchoolClassSerializer(serializers.ModelSerializer):
    streams = StreamSerializer(many=True, read_only=True)

    class Meta:
        model = SchoolClass
        fields = "__all__"


class TimetableEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableEntry
        fields = "__all__"

    def validate(self, data):
        time_slot = data["time_slot"]
        teacher = data["teacher"]
        classroom = data["classroom"]

        qs = TimetableEntry.objects.filter(time_slot=time_slot)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.filter(teacher=teacher).exists():
            raise serializers.ValidationError(f"{teacher} is already scheduled in this time slot.")
        if qs.filter(classroom=classroom).exists():
            raise serializers.ValidationError(f"Classroom {classroom} is already booked in this time slot.")
        return data