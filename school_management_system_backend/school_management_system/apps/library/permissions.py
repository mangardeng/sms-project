from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.parents.services import parent_owns_student


class LibraryAccessPermission(BasePermission):
    """
    Admin/Librarian: full.
    Everyone else: view only (books catalog is generally browsable);
    a parent may only see their own child's borrowing records, and a
    student only their own (3.8 matrix: Library = Limited for most roles).
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return True
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return True
        if request.method not in SAFE_METHODS:
            return False

        student = getattr(obj, "student", None)
        if student is None:
            # Plain Book catalog entries: viewable by anyone authenticated.
            return True
        if user.role == User.Role.PARENT:
            return parent_owns_student(user, student.id)
        if user.role == User.Role.STUDENT:
            return student.user_id == user.id
        # Staff roles (teacher, accountant, head teacher, registrar) can view records generally.
        return True
