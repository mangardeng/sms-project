from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.parents.services import parent_owns_student
from apps.teachers.services import teacher_assigned_to_student


class StudentAccessPermission(BasePermission):
    """
    Implements the 3.8 access matrix for the Student resource:

        Administrator -> Full
        Head Teacher   -> View only
        Registrar      -> Full
        Teacher        -> Assigned classes only
        Parent         -> Own child(ren) only   <-- 3.14 hard requirement
        Student        -> Own record only, read-only

    View-level (has_permission) decides who may even reach the
    viewset/action; object-level (has_object_permission) re-validates
    against the SPECIFIC student instance being requested, which is
    what stops URL manipulation (3.14: "/api/students/25/").
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.REGISTRAR):
            return True

        if user.role == User.Role.HEAD_TEACHER:
            return request.method in SAFE_METHODS

        if user.role == User.Role.ACCOUNTANT:
                    return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            return request.method in SAFE_METHODS

        if user.role == User.Role.PARENT:
            return request.method in SAFE_METHODS

        if user.role == User.Role.STUDENT:
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.REGISTRAR):
            return True

        if user.role == User.Role.HEAD_TEACHER:
            return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            return request.method in SAFE_METHODS and teacher_assigned_to_student(user, obj)

        if user.role == User.Role.PARENT:
            # This is the exact check demanded by 3.14: DENY unless the
            # ParentStudent relationship exists for THIS student id.
            return request.method in SAFE_METHODS and parent_owns_student(user, obj.id)

        if user.role == User.Role.STUDENT:
            return request.method in SAFE_METHODS and obj.user_id == user.id

        return False
