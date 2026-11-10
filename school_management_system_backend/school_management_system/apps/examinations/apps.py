from django.apps import AppConfig


class ExaminationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.examinations"

    def ready(self):
        from apps.examinations import signals  # noqa: F401  (registers the auto-compute hooks)
