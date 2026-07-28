from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated 
            and request.user.role == "ADMIN"
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated 
            and request.user.role in [
                "TEACHER",
                "HEAD_TEACHER"
            ]
        )


class IsParent(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "PARENT"
        )


class IsOwnerOrAdmin(BasePermission):
    """
    User can access own data,
    Admin can access everything.
    """

    def has_object_permission(self, request, view, obj):

        if request.user.role == "ADMIN":
            return True

        return getattr(obj, "user_id", None) == request.user.id