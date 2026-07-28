from rest_framework import serializers
from .models import Teacher, SubjectAllocation

class SubjectAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectAllocation
        fields = "__all__"

class TeacherSerializer(serializers.ModelSerializer):
    allocations = SubjectAllocationSerializer(many=True, read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "user", "employee_id", "date_joined", "subjects_qualified", "full_name", "email", "allocations"]