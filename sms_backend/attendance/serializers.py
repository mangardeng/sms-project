from rest_framework import serializers
from .models import StudentAttendance, TeacherAttendance

class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = StudentAttendance
        fields = ["id", "student", "student_name", "school_class", "date", "status", "recorded_by"]
        read_only_fields = ["recorded_by"]


class TeacherAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAttendance
        fields = ["id", "teacher", "date", "status"]