
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import USER_EDITABLE_FIELDS, UserFieldsUpdateMixin, UserSerializer
from apps.students.models import Student, StudentTransferHistory
from apps.classes.models import SchoolClass


def _validate_stream_in_class(instance, attrs):
    """A stream must belong to the student's class."""
    stream = attrs.get("stream", getattr(instance, "stream", None))
    school_class = attrs.get("school_class", getattr(instance, "school_class", None))
    if stream and school_class and stream.school_class_id != school_class.id:
        raise serializers.ValidationError({"stream": "This stream does not belong to the selected class."})
    if stream and not school_class:
        raise serializers.ValidationError({"stream": "Choose a class before choosing a stream."})
    return attrs


class StudentSerializer(UserFieldsUpdateMixin, serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    school_class_name = serializers.CharField(
        source="school_class.name",
        read_only=True,
        default=None
    )

    stream_name = serializers.CharField(
        source="stream.name",
        read_only=True,
        default=None
    )

    class Meta:
        model = Student
        fields = (
            "id",
            "user",
            "index_number",
            "date_of_birth",
            "gender",
            "address",
            "admission_date",
            "school_class",
            "school_class_name",
            "stream",
            "stream_name",
            "status",
            "photo",
            "emergency_contact_name",
            "emergency_contact_phone",
            *USER_EDITABLE_FIELDS,
        )

        read_only_fields = (
            "index_number",
            "admission_date",
        )

    def validate(self, attrs):
        return _validate_stream_in_class(self.instance, attrs)


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """
    Admin/Registrar endpoint:
    Creates the User (role=student) + Student profile together,
    and auto-generates the index number.
    """

    username = serializers.CharField(
        write_only=True,
        help_text="Login username (index number is generated separately)."
    )

    first_name = serializers.CharField(
        write_only=True
    )

    last_name = serializers.CharField(
        write_only=True
    )

    email = serializers.EmailField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    phone_number = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    password = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = Student

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
            "date_of_birth",
            "gender",
            "address",
            "school_class",
            "stream",
            "photo",
            "emergency_contact_name",
            "emergency_contact_phone",
        )

    def validate(self, attrs):
        return _validate_stream_in_class(None, attrs)

    @transaction.atomic
    def create(self, validated_data):
        user_fields = {
            "username": validated_data.pop("username"),
            "first_name": validated_data.pop("first_name"),
            "last_name": validated_data.pop("last_name"),
            "email": validated_data.pop("email", ""),
            "phone_number": validated_data.pop("phone_number", ""),
        }

        password = validated_data.pop("password")

        user = User(
            role=User.Role.STUDENT,
            must_change_password=True,
            **user_fields
        )

        user.set_password(password)
        user.save()

        return Student.objects.create(
            user=user,
            **validated_data
        )


class StudentTransferSerializer(serializers.Serializer):
    """
    Serializer used when transferring a student from one
    school class to another.
    """

    to_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.filter(is_active=True)
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True
    )

    @transaction.atomic
    def save(self, **kwargs):
        student = self.context["student"]
        request = self.context["request"]

        from_class = student.school_class

        student.school_class = self.validated_data["to_class"]

        # A class transfer resets the student's stream.
        student.stream = None

        student.save(
            update_fields=[
                "school_class",
                "stream",
            ]
        )

        StudentTransferHistory.objects.create(
            student=student,
            from_class=from_class,
            to_class=student.school_class,
            reason=self.validated_data.get("reason", ""),
            transferred_by=request.user,
        )

        return student


class StudentTransferHistorySerializer(serializers.ModelSerializer):
    from_class_name = serializers.CharField(
        source="from_class.name",
        read_only=True,
        default=None
    )

    to_class_name = serializers.CharField(
        source="to_class.name",
        read_only=True,
        default=None
    )

    class Meta:
        model = StudentTransferHistory

        fields = (
            "id",
            "student",
            "from_class_name",
            "to_class_name",
            "reason",
            "transferred_by",
            "created_at",
        )

