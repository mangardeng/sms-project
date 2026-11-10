from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import USER_EDITABLE_FIELDS, UserFieldsUpdateMixin, UserSerializer
from apps.teachers.models import Teacher


class TeacherSerializer(UserFieldsUpdateMixin, serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    assigned_class_count = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = (
            "id", "user", "staff_id", "gender", "date_of_birth", "address",
            "date_employed", "qualification", "photo", "is_active_staff",
            "assigned_class_count",
            *USER_EDITABLE_FIELDS,
        )
        read_only_fields = ("staff_id",)

    def get_assigned_class_count(self, obj):
        return obj.assigned_classes.count()


class TeacherRegistrationSerializer(serializers.ModelSerializer):
    """
    Admin-only endpoint to register a new teacher: creates the User
    account (role=teacher) AND the Teacher profile in one call (3.4.1
    'Register teachers').
    """

    username = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Teacher
        fields = (
            "username", "first_name", "last_name", "email", "phone_number", "password",
            "staff_id", "gender", "date_of_birth", "address", "date_employed", "qualification",
            "photo",
        )

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

        user = User(role=User.Role.TEACHER, must_change_password=True, **user_fields)
        user.set_password(password)
        user.save()

        return Teacher.objects.create(user=user, **validated_data)
