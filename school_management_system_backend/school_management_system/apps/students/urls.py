from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.students.views import MyStudentProfileView, StudentViewSet

router = DefaultRouter()
router.register("me", MyStudentProfileView, basename="student-me")
router.register("", StudentViewSet, basename="student")

urlpatterns = [
    path("", include(router.urls)),
]
