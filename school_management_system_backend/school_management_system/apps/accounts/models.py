from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import UserManager


class User(AbstractUser):
    """
    Custom user model shared by every category of system user
    (Administrator, Head Teacher, Registrar, Teacher, Accountant,
    Librarian, Parent, Student).

    - Staff/admin-type users authenticate with username + password.
    - Students authenticate with their index/admission number + password;
      the Student model (apps.students) stores `index_number` and points
      back to this user via a OneToOne field. The custom authentication
      backend (apps.accounts.backends) resolves an index number to the
      matching User transparently, so this model does not need a
      separate "index_number" field itself.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "System Administrator"
        HEAD_TEACHER = "head_teacher", "Head Teacher"
        REGISTRAR = "registrar", "Registrar"
        TEACHER = "teacher", "Teacher"
        ACCOUNTANT = "accountant", "Accountant"
        LIBRARIAN = "librarian", "Librarian"
        PARENT = "parent", "Parent"
        STUDENT = "student", "Student"

    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    must_change_password = models.BooleanField(
        default=True,
        help_text="Forces a password change on next login for accounts created by an admin.",
    )
    failed_login_attempts = models.PositiveIntegerField(default=0)
    is_locked = models.BooleanField(default=False)

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def dashboard_path(self):
        mapping = {
            self.Role.ADMIN: "/dashboard/admin",
            self.Role.HEAD_TEACHER: "/dashboard/head-teacher",
            self.Role.REGISTRAR: "/dashboard/registrar",
            self.Role.TEACHER: "/dashboard/teacher",
            self.Role.ACCOUNTANT: "/dashboard/accountant",
            self.Role.LIBRARIAN: "/dashboard/librarian",
            self.Role.PARENT: "/dashboard/parent",
            self.Role.STUDENT: "/dashboard/student",
        }
        return mapping.get(self.role, "/dashboard")

    # Convenience role checks -------------------------------------------------
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_head_teacher(self):
        return self.role == self.Role.HEAD_TEACHER

    def is_registrar(self):
        return self.role == self.Role.REGISTRAR

    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    def is_librarian(self):
        return self.role == self.Role.LIBRARIAN

    def is_parent(self):
        return self.role == self.Role.PARENT

    def is_student(self):
        return self.role == self.Role.STUDENT


class PasswordResetToken(models.Model):
    """One-time token used for secure password reset links."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone

        return not self.used and self.expires_at > timezone.now()
