from rest_framework.routers import DefaultRouter
from .views import AcademicYearViewSet, SchoolClassViewSet, StreamViewSet, TimetableEntryViewSet

router = DefaultRouter()
router.register("academic-years", AcademicYearViewSet)
router.register("classes", SchoolClassViewSet)
router.register("streams", StreamViewSet)

router.register(
    "timetable",
    TimetableEntryViewSet
)


urlpatterns = router.urls