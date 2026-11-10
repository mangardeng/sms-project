from rest_framework import serializers

from apps.subjects.models import ClassSubject, Subject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "name", "code", "is_compulsory", "description")


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True, default=None)

    class Meta:
        model = ClassSubject
        fields = (
            "id", "school_class", "school_class_name", "subject", "subject_name",
            "teacher", "teacher_name", "academic_year",
        )
