from rest_framework.routers import DefaultRouter

from apps.classes.views import SchoolClassViewSet, StreamViewSet

router = DefaultRouter()
router.register("streams", StreamViewSet, basename="stream")
router.register("", SchoolClassViewSet, basename="schoolclass")

urlpatterns = router.urls
