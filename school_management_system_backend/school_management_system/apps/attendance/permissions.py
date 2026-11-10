from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.parents.services import parent_owns_student
from apps.teachers.services import teacher_assigned_to_class


class AttendanceAccessPermission(BasePermission):
    """
    Administrator/Head Teacher/Registrar: view all (Head Teacher/Registrar read-only).
    Teacher: record/edit attendance ONLY for their assigned classes (3.4.4, 3.10.7).
    Parent: view only their linked child's attendance (3.14).
    Student: view only their own attendance.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            return True  # further scoped to assigned classes at object/queryset level

        if user.role in (User.Role.PARENT, User.Role.STUDENT):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            return teacher_assigned_to_class(user, obj.school_class_id)

        if user.role == User.Role.PARENT:
            return request.method in SAFE_METHODS and parent_owns_student(user, obj.student_id)

        if user.role == User.Role.STUDENT:
            return request.method in SAFE_METHODS and obj.student.user_id == user.id

        return False
