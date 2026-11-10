from rest_framework import serializers

from apps.classes.models import SchoolClass, Stream


class StreamSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = ("id", "school_class", "school_class_name", "name", "capacity", "student_count")

    def get_student_count(self, obj):
        return obj.students.filter(status="active").count()


class SchoolClassSerializer(serializers.ModelSerializer):
    class_teacher_name = serializers.CharField(source="class_teacher.user.get_full_name", read_only=True, default=None)
    streams = StreamSerializer(many=True, read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = (
            "id", "name", "level", "class_teacher", "class_teacher_name",
            "is_active", "streams", "student_count",
        )

    def get_student_count(self, obj):
        return obj.students.filter(status="active").count()
