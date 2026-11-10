from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def frontend(request):
    return redirect("http://localhost:3000/")


urlpatterns = [
    # React Frontend
    path("", frontend, name="frontend"),

    # Django Admin
    path("admin/", admin.site.urls),

    # Authentication
    path("api/auth/", include("apps.accounts.urls")),

    # Shared calendar structure (academic years / terms)
    path("api/", include("apps.core.urls")),

    # Domain modules
    path("api/students/", include("apps.students.urls")),
    path("api/teachers/", include("apps.teachers.urls")),
    path("api/parents/", include("apps.parents.urls")),
    path("api/classes/", include("apps.classes.urls")),
    path("api/subjects/", include("apps.subjects.urls")),
    path("api/attendance/", include("apps.attendance.urls")),
    path("api/examinations/", include("apps.examinations.urls")),
    path("api/fees/", include("apps.fees.urls")),
    path("api/library/", include("apps.library.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),

    # API schema / documentation
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]


# Serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )