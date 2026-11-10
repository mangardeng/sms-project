from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import USER_EDITABLE_FIELDS, UserFieldsUpdateMixin, UserSerializer
from apps.parents.models import Parent, ParentStudent
from apps.students.models import Student


class ParentStudentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    parent_name = serializers.CharField(source="parent.user.get_full_name", read_only=True)

    class Meta:
        model = ParentStudent
        fields = (
            "id", "parent", "parent_name", "student", "student_name",
            "student_index_number", "relationship", "is_primary_contact",
        )


class ParentSerializer(UserFieldsUpdateMixin, serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    linked_students = ParentStudentSerializer(source="student_links", many=True, read_only=True)

    class Meta:
        model = Parent
        fields = (
            "id", "user", "address", "occupation", "alternate_phone", "linked_students",
            *USER_EDITABLE_FIELDS,
        )


class ParentRegistrationSerializer(serializers.ModelSerializer):
    """Admin/Registrar endpoint: creates the User (role=parent) + Parent profile (3.10.4)."""

    username = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    student_ids = serializers.PrimaryKeyRelatedField(
        source="students", queryset=Student.objects.all(), many=True, write_only=True, required=False
    )
    relationship = serializers.ChoiceField(
        choices=ParentStudent.Relationship.choices, write_only=True, required=False,
        default=ParentStudent.Relationship.GUARDIAN,
    )

    class Meta:
        model = Parent
        fields = (
            "username", "first_name", "last_name", "email", "phone_number", "password",
            "address", "occupation", "alternate_phone", "student_ids", "relationship",
        )

    @transaction.atomic
    def create(self, validated_data):
        student_list = validated_data.pop("students", [])
        relationship = validated_data.pop("relationship", ParentStudent.Relationship.GUARDIAN)

        user_fields = {
            "username": validated_data.pop("username"),
            "first_name": validated_data.pop("first_name"),
            "last_name": validated_data.pop("last_name"),
            "email": validated_data.pop("email", ""),
            "phone_number": validated_data.pop("phone_number", ""),
        }
        password = validated_data.pop("password")

        user = User(role=User.Role.PARENT, must_change_password=True, **user_fields)
        user.set_password(password)
        user.save()

        parent = Parent.objects.create(user=user, **validated_data)

        # This is where the critical parent<->student relationship (3.13/3.14) is created.
        for student in student_list:
            ParentStudent.objects.create(parent=parent, student=student, relationship=relationship)

        return parent
