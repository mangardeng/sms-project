from rest_framework import serializers
from .models import Student, Guardian, StudentTransferLog

class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = "__all__"

class StudentSerializer(serializers.ModelSerializer):
    guardians = GuardianSerializer(many=True, read_only=True)
    stream_name = serializers.CharField(source="stream.__str__", read_only=True)

    class Meta:
        model = Student
        fields = "__all__"

class StudentTransferLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentTransferLog
        fields = "__all__"