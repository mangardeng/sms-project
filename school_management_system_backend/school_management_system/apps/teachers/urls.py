from rest_framework.routers import DefaultRouter
from django.urls import include, path

from apps.teachers.views import MyTeacherProfileView, TeacherViewSet

router = DefaultRouter()
router.register("", TeacherViewSet, basename="teacher")

urlpatterns = [
    path("me/", MyTeacherProfileView.as_view(), name="teacher-me"),
    path("", include(router.urls)),
]
