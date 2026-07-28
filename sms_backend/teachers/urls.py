from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, SubjectAllocationViewSet

router = DefaultRouter()
router.register("teachers", TeacherViewSet)
router.register("allocations", SubjectAllocationViewSet)

urlpatterns = router.urls