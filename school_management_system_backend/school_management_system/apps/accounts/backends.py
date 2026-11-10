from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class UsernameOrIndexNumberBackend(ModelBackend):
    """
    Authenticates staff-type users (admin, head teacher, registrar,
    teacher, accountant, librarian, parent) using `username`, and
    students using their unique student index/admission number,
    through the SAME login endpoint — matching the "one authentication
    mechanism capable of identifying different types of users" design
    (see design doc section 3.5 / 3.7).

    The frontend simply POSTs whatever the user typed (username or
    index number) as `username`; this backend figures out which one
    it is.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = self._find_user(username)
        if user is None:
            return None

        if user.is_locked or not user.is_active:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    @staticmethod
    def _find_user(identifier):
        # 1) Try a normal username match (covers all non-student roles).
        try:
            return User.objects.get(username__iexact=identifier)
        except User.DoesNotExist:
            pass

        # 2) Fall back to student index/admission number.
        # Imported lazily to avoid a circular import between accounts <-> students.
        from apps.students.models import Student

        try:
            student = Student.objects.select_related("user").get(index_number__iexact=identifier)
            return student.user
        except Student.DoesNotExist:
            return None
