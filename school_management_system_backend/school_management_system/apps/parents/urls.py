from rest_framework.routers import DefaultRouter

from apps.parents.views import ParentStudentLinkViewSet, ParentViewSet

router = DefaultRouter()
router.register("links", ParentStudentLinkViewSet, basename="parentstudent")
router.register("", ParentViewSet, basename="parent")

urlpatterns = router.urls
