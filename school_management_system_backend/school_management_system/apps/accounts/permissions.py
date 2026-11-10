"""
Reusable role-based access control (RBAC) permission classes.

The design doc is explicit that "role information must not be trusted
solely from the React application" and that Django must validate the
user's role and permissions on EVERY protected API request (3.6). All
of these classes therefore re-check `request.user.role` on every call,
server-side, regardless of anything the client sends.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


def has_role(user, *roles):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role in roles))


class IsAdmin(BasePermission):
    message = "Only a system administrator can perform this action."

    def has_permission(self, request, view):
        return has_role(request.user, User.Role.ADMIN)


class IsHeadTeacher(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.HEAD_TEACHER)


class IsRegistrar(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.REGISTRAR)


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.TEACHER)


class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.ACCOUNTANT)


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.LIBRARIAN)


class IsParent(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.PARENT)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.STUDENT)


class IsAdminOrRegistrar(BasePermission):
    """Full student-management rights (3.4.1 / 3.4.3)."""

    def has_permission(self, request, view):
        return has_role(request.user, User.Role.ADMIN, User.Role.REGISTRAR)


class IsAdminOrHeadTeacher(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, User.Role.ADMIN, User.Role.HEAD_TEACHER)


class ReadOnlyForHeadTeacher(BasePermission):
    """Head Teacher has view-only access almost everywhere (3.8 access matrix)."""

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.role == User.Role.HEAD_TEACHER:
            return request.method in SAFE_METHODS
        return True


class HasAnyRole(BasePermission):
    """
    Generic factory-style permission. Usage:

        permission_classes = [HasAnyRole.for_roles(User.Role.ADMIN, User.Role.ACCOUNTANT)]
    """

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        return has_role(request.user, *self.allowed_roles)

    @classmethod
    def for_roles(cls, *roles):
        return type("HasAnyRoleConfigured", (cls,), {"allowed_roles": roles})


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: the requesting user IS the linked user, or is an admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if has_role(user, User.Role.ADMIN):
            return True
        owner_user = getattr(obj, "user", obj)
        return owner_user == user
