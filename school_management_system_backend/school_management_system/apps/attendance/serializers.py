from django.db import transaction
from rest_framework import serializers

from apps.attendance.models import Attendance
from apps.students.models import Student
from apps.classes.models import SchoolClass


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student.user.get_full_name",
        read_only=True
    )
    student_index_number = serializers.CharField(
        source="student.index_number",
        read_only=True
    )
    school_class_name = serializers.CharField(
        source="school_class.name",
        read_only=True
    )

    class Meta:
        model = Attendance
        fields = (
            "id",
            "student",
            "student_name",
            "student_index_number",
            "school_class",
            "school_class_name",
            "date",
            "status",
            "remarks",
            "recorded_by",
        )
        read_only_fields = ("recorded_by",)


class BulkAttendanceEntrySerializer(serializers.Serializer):
    student = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all()
    )
    status = serializers.ChoiceField(
        choices=Attendance.Status.choices
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True
    )


class BulkAttendanceSerializer(serializers.Serializer):
    """
    POST payload for recording a whole class's attendance for one day
    in a single request:

        {
          "school_class": 3,
          "date": "2026-09-05",
          "entries": [
              {
                  "student": 12,
                  "status": "present"
              }
          ]
        }
    """

    school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.all()
    )

    date = serializers.DateField()

    entries = BulkAttendanceEntrySerializer(
        many=True
    )

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context["request"]

        school_class = self.validated_data["school_class"]
        date = self.validated_data["date"]

        records = []

        for entry in self.validated_data["entries"]:
            record, _created = Attendance.objects.update_or_create(
                student=entry["student"],
                date=date,
                defaults={
                    "school_class": school_class,
                    "status": entry["status"],
                    "remarks": entry.get("remarks", ""),
                    "recorded_by": request.user,
                },
            )

            records.append(record)

        return records