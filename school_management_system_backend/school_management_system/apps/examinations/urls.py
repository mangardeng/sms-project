from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.examinations.sheet import SubjectSheetOptionsView, SubjectSheetView
from apps.examinations.views import (
    ExaminationResultViewSet,
    ExaminationTypeViewSet,
    ExaminationViewSet,
    GradeBoundaryViewSet,
    SubjectTermResultViewSet,
    TermSummaryViewSet,
)

router = DefaultRouter()
router.register("types", ExaminationTypeViewSet, basename="examinationtype")
router.register("results", ExaminationResultViewSet, basename="examinationresult")
router.register("grade-scale", GradeBoundaryViewSet, basename="gradeboundary")
router.register("term-results", SubjectTermResultViewSet, basename="subjecttermresult")
router.register("term-summaries", TermSummaryViewSet, basename="termsummary")
router.register("", ExaminationViewSet, basename="examination")

urlpatterns = [
    # Must come before the router, whose empty prefix would otherwise treat "subject-sheet" as an exam id.
    path("subject-sheet/options/", SubjectSheetOptionsView.as_view(), name="subject-sheet-options"),
    path("subject-sheet/", SubjectSheetView.as_view(), name="subject-sheet"),
] + router.urls
