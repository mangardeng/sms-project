from django.contrib import admin
from django.urls import path, include
from core.views import PingView


from accounts.views import RoleTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/login/",
        RoleTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/login/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path("api/ping/", PingView.as_view()
         ),

    path("api/academics/", include("academics.urls")),

    path("api/teachers/", include("teachers.urls")),

    path("api/students/", include("students.urls")),

    path(
        "api/attendance/",
        include("attendance.urls")
    ),
]