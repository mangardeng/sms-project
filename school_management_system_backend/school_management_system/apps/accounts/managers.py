from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    """
    Ensures `python manage.py createsuperuser` produces a fully-formed
    Administrator account (role=admin) rather than leaving `role` blank,
    since `role` isn't part of Django's default createsuperuser prompts.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("must_change_password", False)
        return super().create_superuser(username, email, password, **extra_fields)
