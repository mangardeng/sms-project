from rest_framework.routers import DefaultRouter

from apps.core.views import AcademicYearViewSet, TermViewSet

router = DefaultRouter()
router.register("academic-years", AcademicYearViewSet, basename="academicyear")
router.register("terms", TermViewSet, basename="term")

urlpatterns = router.urls
