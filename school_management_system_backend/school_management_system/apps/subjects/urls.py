from rest_framework.routers import DefaultRouter

from apps.subjects.views import ClassSubjectViewSet, SubjectViewSet

router = DefaultRouter()
router.register("assignments", ClassSubjectViewSet, basename="classsubject")
router.register("", SubjectViewSet, basename="subject")

urlpatterns = router.urls
