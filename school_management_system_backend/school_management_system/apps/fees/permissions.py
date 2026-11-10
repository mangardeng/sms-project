from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.parents.services import parent_owns_student


class FeeAccessPermission(BasePermission):
    """
    Admin/Accountant: full.
    Head Teacher: view only.
    Registrar: view only (3.8 matrix: Registrar Fees = View).
    Teacher/Librarian: no access.
    Parent/Student: view own/linked child's fee info only (3.14).
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.ACCOUNTANT):
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role in (User.Role.PARENT, User.Role.STUDENT):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        student = getattr(obj, "student", None)

        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.ACCOUNTANT):
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role == User.Role.PARENT and student is not None:
            return request.method in SAFE_METHODS and parent_owns_student(user, student.id)

        if user.role == User.Role.STUDENT and student is not None:
            return request.method in SAFE_METHODS and student.user_id == user.id

        if student is None:
            # Objects with no per-student linkage (e.g. a FeeStructure /
            # class fee schedule) are not individually sensitive — any
            # authenticated user may view them, subject to has_permission.
            return request.method in SAFE_METHODS

        return False


class FinanceAccessPermission(BasePermission):
    """
    Sponsors, carry-forward, expenses, other income, staff salaries and the finance summary.
    Admin/Accountant: full. Head Teacher: view only. Everyone else (including parents and
    students): no access.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.ACCOUNTANT):
            return True
        if user.role == User.Role.HEAD_TEACHER:
            return request.method in SAFE_METHODS
        return False


def is_accountant(user) -> bool:
    """Payments may only be corrected or voided by the accountant."""
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == User.Role.ACCOUNTANT))
