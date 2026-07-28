from rest_framework.routers import DefaultRouter
from .views import (
    StudentAttendanceViewSet,
    TeacherAttendanceViewSet,
)

router = DefaultRouter()

router.register(
    "students",
    StudentAttendanceViewSet,
    basename="student-attendance"
)

router.register(
    "teachers",
    TeacherAttendanceViewSet,
    basename="teacher-attendance"
)

urlpatterns = router.urls